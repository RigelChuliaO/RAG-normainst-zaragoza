"""Juez LLM de fidelidad y su calibración contra el criterio humano (Fase 2).

Tres pasos, en este orden (el humano juzga ANTES de ver al juez: a ciegas):

  1. sample   Elige 15 respuestas y escribe eval/calibration/sample.md (pregunta,
              fragmentos citados, respuesta) y labels.csv para rellenar a mano.
  2. judge    Pasa el juez LLM por todas las respuestas de un resultado de
              generación y guarda <resultado>_judged.json.
  3. compare  Compara tus etiquetas con las del juez: acuerdo, kappa de Cohen,
              matriz de confusión y los desacuerdos uno a uno.

Uso (desde la raíz del repo):
  python eval/calibrate.py sample  eval/results/<fichero>_generation_e5-base_rescored.json
  python eval/calibrate.py judge   eval/results/<fichero>_generation_e5-base_rescored.json
  python eval/calibrate.py compare eval/results/<fichero>_judged.json
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
CHUNKS_FILE = ROOT / "data" / "processed" / "BOE-A-2007-15820-consolidado.chunks.jsonl"
CAL_DIR = ROOT / "eval" / "calibration"
# Casos difíciles que SIEMPRE entran en la muestra: un juez que solo acierta en
# los fáciles no sirve. q28-q30 inventan «Sí, puede»; q18, q25 y q31 son mixtas;
# q02 se apoya en un RITE que se contradice; q34 y q06 son fieles pero incompletas.
MUST_SAMPLE = ["q28", "q29", "q30", "q18", "q25", "q31", "q02", "q34", "q06"]


def load_chunks() -> dict[str, SimpleNamespace]:
    """id -> chunk con lo que necesita format_context (unit, title, page_start, text)."""
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        return {c["id"]: SimpleNamespace(**{k: c[k] for k in ("id", "unit", "title", "page_start", "text")})
                for c in map(json.loads, f)}


def judgeable(row: dict) -> bool:
    """Solo se juzgan respuestas que afirman algo (no las que son solo «No consta»)."""
    return "answer" in row and not row.get("no_consta") and "error" not in row


# --- 1. muestra para etiquetar a mano --------------------------------------------

def cmd_sample(args) -> None:
    data = json.loads(args.results.read_text(encoding="utf-8"))
    rows = [r for r in data["questions"] if judgeable(r)]
    by_id = {r["id"]: r for r in rows}
    chosen = [by_id[i] for i in MUST_SAMPLE if i in by_id]
    rest = [r for r in rows if r["id"] not in {c["id"] for c in chosen}]
    random.Random(0).shuffle(rest)                      # semilla fija: la misma muestra siempre
    chosen += rest[: max(0, args.n - len(chosen))]
    chosen.sort(key=lambda r: r["id"])
    chunks = load_chunks()

    CAL_DIR.mkdir(parents=True, exist_ok=True)
    md = ["# Calibración del juez: fidelidad", "",
          "Para cada respuesta decide: ¿TODAS sus afirmaciones están en los fragmentos?",
          "- **si** (fiel): nada inventado, aunque esté incompleta.",
          "- **no** (no fiel): al menos una afirmación no está en los fragmentos, los contradice o los aplica a otro caso.",
          "", "Apunta tu veredicto en `labels.csv` (columna `fiel`: si / no) ANTES de mirar lo que dice el juez.",
          "Abajo van completos los fragmentos que la respuesta cita; de los demás, solo el título.", ""]
    for r in chosen:
        cited = set(r["cited"])
        md += [f"---", "", f"## {r['id']} · {r['question']}", "", "**Respuesta del modelo:**", "",
               "> " + r["answer"].replace("\n", "\n> "), "", "**Fragmentos que recibió:**", ""]
        for n, cid in enumerate(r["retrieved"], start=1):
            c = chunks.get(cid)
            if c is None:
                continue
            head = f"[{n}] {c.unit}. {c.title} (pág. {c.page_start})"
            if cid in cited:
                md += [f"**{head}** — citado", "", "```", c.text, "```", ""]
            else:
                md += [f"- {head} — no citado", ""]
    (CAL_DIR / "sample.md").write_text("\n".join(md), encoding="utf-8")
    labels = CAL_DIR / "labels.csv"
    if labels.exists() and not args.force:
        print(f"{labels.relative_to(ROOT)} ya existe: no lo piso (usa --force)")
    else:
        with open(labels, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "fiel", "afirmacion_no_respaldada"])
            for r in chosen:
                w.writerow([r["id"], "", ""])
    print(f"muestra de {len(chosen)}: {', '.join(r['id'] for r in chosen)}")
    print(f"lee {(CAL_DIR / 'sample.md').relative_to(ROOT)} y rellena {labels.relative_to(ROOT)}")


# --- 2. el juez sobre todas las respuestas ---------------------------------------

def cmd_judge(args) -> None:
    from rag_normainst.generate import DEFAULT_LLM, make_client
    from rag_normainst.judge import judge

    data = json.loads(args.results.read_text(encoding="utf-8"))
    chunks = load_chunks()
    client, llm = make_client(), args.llm or DEFAULT_LLM
    rows = data["questions"]
    todo = [r for r in rows if judgeable(r)]
    print(f"juez {llm}: {len(todo)} respuestas que afirman algo (de {len(rows)})")
    t0 = time.perf_counter()
    for n, r in enumerate(todo, start=1):
        hits = [chunks[c] for c in r["retrieved"] if c in chunks]
        v = judge(r["answer"], hits, client, llm)
        r["judge"] = {"faithful": v.faithful, "claim": v.claim, "reason": v.reason, "raw": v.raw}
        tag = {True: "fiel", False: "NO FIEL", None: "ilegible"}[v.faithful]
        print(f"  [{n:>2}/{len(todo)}] {r['id']} {tag}" + (f" · «{v.claim[:80]}»" if v.claim else ""))
    verdicts = [r["judge"]["faithful"] for r in todo]
    print(f"tiempo: {(time.perf_counter() - t0) / 60:.1f} min · fieles {verdicts.count(True)} · "
          f"no fieles {verdicts.count(False)} · ilegibles {verdicts.count(None)}")
    data["config"]["judge"] = llm
    out = args.results.with_name(args.results.stem + "_judged.json")
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"guardado en {out.resolve().relative_to(ROOT)}")


# --- 3. comparación humano / juez ------------------------------------------------

def cohen_kappa(pairs: list[tuple[bool, bool]]) -> float:
    """Acuerdo corregido por azar: 1 perfecto, 0 lo mismo que tirar una moneda."""
    n = len(pairs)
    if n == 0:
        return float("nan")
    po = sum(a == b for a, b in pairs) / n
    pa, pb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def cmd_compare(args) -> None:
    data = json.loads(args.judged.read_text(encoding="utf-8"))
    judged = {r["id"]: r for r in data["questions"] if "judge" in r}
    with open(args.labels, encoding="utf-8") as f:
        labels = {row["id"]: row for row in csv.DictReader(f)}
    pairs, rows = [], []
    for qid, lab in labels.items():
        h = lab["fiel"].strip().lower()
        if h not in ("si", "sí", "no") or qid not in judged:
            continue
        human = h != "no"
        j = judged[qid]["judge"]["faithful"]
        rows.append((qid, human, j, lab.get("afirmacion_no_respaldada", ""), judged[qid]["judge"]))
        if j is not None:
            pairs.append((human, j))
    if not rows:
        print("no hay etiquetas: rellena la columna 'fiel' (si / no) de labels.csv")
        return
    agree = sum(a == b for a, b in pairs)
    cm = {(h, j): sum(1 for a, b in pairs if (a, b) == (h, j)) for h in (True, False) for j in (True, False)}
    print(f"etiquetadas: {len(rows)} · con veredicto legible del juez: {len(pairs)}")
    print(f"ACUERDO: {agree}/{len(pairs)} = {agree / len(pairs):.2f} · kappa de Cohen {cohen_kappa(pairs):.2f}")
    print("\n                  juez: fiel   juez: no fiel")
    print(f"  tú: fiel        {cm[(True, True)]:>9}   {cm[(True, False)]:>12}")
    print(f"  tú: no fiel     {cm[(False, True)]:>9}   {cm[(False, False)]:>12}")
    print("\n  (lo peligroso es «tú: no fiel / juez: fiel»: el juez deja pasar invenciones)")
    bad = [r for r in rows if r[2] != r[1]]
    if bad:
        print(f"\nDESACUERDOS ({len(bad)}):")
        for qid, human, j, note, jd in bad:
            print(f"  {qid}: tú {'fiel' if human else 'NO fiel'} · juez {({True: 'fiel', False: 'NO fiel', None: 'ilegible'})[j]}")
            if note:
                print(f"      tu nota: {note}")
            if jd.get("claim") or jd.get("reason"):
                print(f"      juez: «{jd.get('claim', '')}» · {jd.get('reason', '')}")
    print("\nRegla práctica: kappa >= 0,6 y ninguna invención que el juez deje pasar -> se puede usar su nota;"
          " si no, la nota oficial sigue siendo la del código y el juez queda como alarma.")


def main() -> None:
    p = argparse.ArgumentParser(description="Juez LLM de fidelidad y su calibración.")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample", help="muestra para etiquetar a mano")
    s.add_argument("results", type=Path)
    s.add_argument("-n", type=int, default=15)
    s.add_argument("--force", action="store_true")
    j = sub.add_parser("judge", help="pasa el juez LLM por las respuestas")
    j.add_argument("results", type=Path)
    j.add_argument("--llm", default=None)
    c = sub.add_parser("compare", help="compara tus etiquetas con el juez")
    c.add_argument("judged", type=Path)
    c.add_argument("--labels", type=Path, default=CAL_DIR / "labels.csv")
    args = p.parse_args()
    {"sample": cmd_sample, "judge": cmd_judge, "compare": cmd_compare}[args.cmd](args)


if __name__ == "__main__":
    main()
