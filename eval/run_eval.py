"""Evaluación del RAG contra el golden set (Fase 2).

Dos etapas, que se miden por separado:
  - retrieval:  solo el retriever (sin LLM, segundos). hit@k, recall@k y MRR.
  - generation: el RAG completo (con Ollama, ~15 s por pregunta). Corrección hecha
                por código: «no consta», datos obligatorios y prohibidos, citas,
                y diagnóstico de cada fallo (¿falló la recuperación o el modelo?).
                Guarda los textos de las respuestas para el juez LLM.
Ambas dan medias en total, por split (dev / holdout) y por tipo de pregunta.

Cada ejecución se guarda fechada en eval/results/ para comparar cambios
(regression suite): el mismo examen, corregido igual, antes y después.

Uso (desde la raíz del repo, con el entorno activado):
  python eval/run_eval.py --pipeline pure
  python eval/run_eval.py --pipeline pure --no-lookup        # sin la búsqueda por id
  python eval/run_eval.py --pipeline pure --model e5-small   # otro índice de embeddings
  python eval/run_eval.py --pipeline pure --stage generation  # RAG completo (Ollama en marcha)
  python eval/run_eval.py --pipeline pure --stage generation --ids q06,q37   # solo algunas
  python eval/run_eval.py --rescore eval/results/<fichero>_generation_<modelo>.json
      # vuelve a corregir respuestas ya guardadas (sin LLM): para cuando cambia el
      # corrector o el golden set, no el sistema
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

from rag_normainst.embeddings import DEFAULT_MODEL, MODELS
from rag_normainst.metrics import aggregate, group_by, load_golden, score_generation, score_retrieval

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLDEN = ROOT / "eval" / "golden_set.jsonl"
RESULTS_DIR = ROOT / "eval" / "results"
CHUNKS_FILE = ROOT / "data" / "processed" / "BOE-A-2007-15820-consolidado.chunks.jsonl"
KS = (1, 3, 5, 10)        # se recupera una vez con el k mayor y se recorta para los demás
MAIN_K = 5                # el k que usa el RAG (pipeline.py): el que importa para fallos


def git_commit() -> str:
    """Commit actual, para saber qué código produjo cada resultado."""
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip()
        return out + ("+cambios" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "desconocido"


def run_retrieval(questions: list[dict], retriever, lookup: bool) -> list[dict]:
    """Recupera los chunks de cada pregunta y calcula sus métricas."""
    k_max = max(KS)
    rows = []
    for q in questions:
        hits = (retriever.search_with_lookup(q["question"], k_max) if lookup
                else retriever.search(q["question"], k_max))
        retrieved = [h.id for h in hits][:k_max]
        row = {"id": q["id"], "type": q["type"], "split": q["split"], "question": q["question"],
               "expected": q["expected"], "retrieved": retrieved,
               "top1_score": round(hits[0].score, 4) if hits else None}
        if q["expected"]:                       # las sin respuesta no tienen nada que encontrar
            row.update(score_retrieval(q, retrieved, KS))
        rows.append(row)
    return rows


def load_chunk_texts() -> dict[str, str]:
    """id -> texto de cada chunk, para saber si los datos llegaron al LLM."""
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        return {c["id"]: c["text"] for c in map(json.loads, f)}


def score_row(q: dict, row: dict, texts: dict[str, str]) -> dict:
    """Corrige una respuesta guardada en `row` (sirve en vivo y al recorregir)."""
    from rag_normainst.generate import is_no_consta, mentions_no_consta

    text = row["answer"]
    said = is_no_consta(text)
    mixed = mentions_no_consta(text) and not said
    context = "\n".join(texts.get(cid, "") for cid in row["retrieved"])
    row["no_consta"] = said
    row.update(score_generation(q, text, said, row["cited"], row.get("invalid_labels", []),
                                row["retrieved"], context=context, mixed_no_consta=mixed))
    return row


def run_generation(questions: list[dict], rag) -> list[dict]:
    """Pasa cada pregunta por el RAG completo y la corrige con código."""
    rows = []
    texts = load_chunk_texts()
    for n, q in enumerate(questions, start=1):
        row = {"id": q["id"], "type": q["type"], "split": q["split"], "question": q["question"],
               "expected": q["expected"]}
        try:
            a = rag.answer(q["question"])
        except Exception as exc:          # una pregunta rota no tumba toda la evaluación
            row.update({"error": str(exc), "correct": False, "complete": False, "diagnosis": "error",
                        "abstention": "error"})
            print(f"  [{n:>2}/{len(questions)}] {q['id']} ERROR: {exc}")
            rows.append(row)
            continue
        row.update({"answer": a.text, "retrieved": a.retrieved_ids,
                    "cited": [c.id for c in a.citations], "invalid_labels": a.invalid_labels,
                    "prompt_tokens": a.prompt_tokens, "completion_tokens": a.completion_tokens,
                    "seconds": round(a.seconds_retrieve + a.seconds_generate, 1)})
        score_row(q, row, texts)
        mark = "bien " if row["correct"] else "FALLO"
        print(f"  [{n:>2}/{len(questions)}] {q['id']} {mark} {row['seconds']:>5.1f} s · {row['diagnosis']}")
        rows.append(row)
    return rows


def summarize_generation(rows: list[dict]) -> dict:
    """Medias y recuentos de la etapa de generación."""
    ok = [r for r in rows if "error" not in r]
    answerable = [r for r in ok if r["expected"]]
    count = lambda field: {v: sum(r.get(field) == v for r in rows) for v in sorted({r.get(field) for r in rows})}
    mean = lambda xs: sum(xs) / len(xs) if xs else 0.0
    return {
        "total": aggregate(rows, ["correct", "complete"]),
        "by_split": group_by(rows, "split", ["correct", "complete"]),
        "by_type": group_by(rows, "type", ["correct", "complete"]),
        "abstention": count("abstention"),
        "diagnosis": count("diagnosis"),
        "coverage_mean": mean([r["coverage"] for r in answerable]),
        "cites_expected": mean([r["cites_expected"] for r in answerable if not r["no_consta"]]),
        "citation_recall": mean([r["citation_recall"] for r in answerable if not r["no_consta"]]),
        "invalid_citations": sum(bool(r["invalid_labels"]) for r in ok),
        "mixed_no_consta": sum(bool(r.get("mixed_no_consta")) for r in ok),
        "no_citation": sum(r["n_citations"] == 0 and not r["no_consta"] for r in ok),
        "seconds_mean": mean([r["seconds"] for r in ok]),
    }


def print_generation(s: dict, rows: list[dict]) -> None:
    t = s["total"]
    print(f"\nSEGÚN EL CÓDIGO ({t['n']} preguntas): correctas {t['correct']:.2f} · completas {t['complete']:.2f}"
          "  (completa = correcta y cita todas las unidades esperadas)")
    print("  por split: " + " · ".join(f"{k} {v['correct']:.2f}/{v['complete']:.2f} (n={v['n']})"
                                     for k, v in s["by_split"].items()))
    print(f"  por tipo:{'':<19}n  correcta completa")
    for k, v in s["by_type"].items():
        print(f"    {k:<24}{v['n']:>3}  {v['correct']:>8.2f} {v['complete']:>8.2f}")
    a = s["abstention"]
    print("\n«NO CONSTA» (las cuatro casillas):")
    print(f"  había respuesta   -> respondió {a.get('responde_cuando_consta', 0):>3} · dijo «No consta» {a.get('no_consta_indebido', 0):>3}")
    print(f"  no había respuesta -> respondió {a.get('inventa', 0):>3} · dijo «No consta» {a.get('no_consta_correcto', 0):>3}")
    print(f"\nDIAGNÓSTICO: {s['diagnosis']}")
    print(f"datos obligatorios presentes (media): {s['coverage_mean']:.2f} · cita la unidad esperada: "
          f"{s['cites_expected']:.2f} · recall de citas: {s['citation_recall']:.2f} · respuestas sin cita: {s['no_citation']} · con citas inválidas: "
          f"{s['invalid_citations']} · tiempo medio {s['seconds_mean']:.1f} s")
    print(f"respuestas MIXTAS (responden y añaden «No consta»): {s['mixed_no_consta']}")
    incomplete = [r for r in rows if r["correct"] and not r["complete"]]
    if incomplete:
        print("\nCORRECTAS PERO INCOMPLETAS (no citan todas las unidades): "
              + ", ".join(f"{r['id']} ({r['citation_recall']:.2f})" for r in incomplete))
    fails = [r for r in rows if not r["correct"]]
    print(f"\nFALLOS ({len(fails)}):")
    for r in fails:
        extra = f" · prohibido: {r['forbidden']}" if r.get("forbidden") else ""
        cov = f" · datos {r['coverage']:.2f}" if r.get("coverage") is not None else ""
        print(f"  {r['id']} [{r['type']}] {r.get('diagnosis')} · {r.get('abstention')}{cov}{extra}")
        print(f"      «{r['question']}»")
        print(f"      -> {r.get('answer', r.get('error', ''))[:220].replace(chr(10), ' ')}")


def metric_keys() -> list[str]:
    return [f"hit@{k}" for k in KS] + [f"recall@{k}" for k in KS] + ["rr"]


def print_table(title: str, groups: dict[str, dict]) -> None:
    """Tabla compacta: una fila por grupo, columnas hit@k, recall@5 y MRR."""
    cols = [f"hit@{k}" for k in KS] + [f"recall@{MAIN_K}", "rr"]
    print(f"\n{title}")
    print(f"  {'grupo':<24}{'n':>3}  " + "  ".join(f"{c.replace('rr', 'MRR'):>9}" for c in cols))
    for name, m in groups.items():
        print(f"  {name:<24}{m['n']:>3}  " + "  ".join(f"{m[c]:>9.2f}" for c in cols))


def save_result(args, stage: str, summary: dict, rows: list[dict], extra: dict | None = None) -> None:
    """Guarda el resultado fechado en eval/results/ (la memoria de la regression suite)."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    suffix = ("_nolookup" if args.no_lookup else "") + ("_subset" if args.ids else "")
    out = RESULTS_DIR / f"{stamp}_{args.pipeline}_{stage}_{args.model}{suffix}.json"
    config = {"pipeline": args.pipeline, "stage": stage, "model": args.model,
              "lookup": not args.no_lookup, "golden": args.golden.name, "ids": args.ids,
              "commit": git_commit(), "date": datetime.now().isoformat(timespec="seconds"),
              **(extra or {})}
    out.write_text(json.dumps({"config": config, "summary": summary, "questions": rows},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nguardado en {out.resolve().relative_to(ROOT)}")


def rescore(args) -> None:
    """Vuelve a corregir un resultado de generación guardado, con el golden set actual."""
    data = json.loads(args.rescore.read_text(encoding="utf-8"))
    golden = {q["id"]: q for q in load_golden(args.golden)}
    texts = load_chunk_texts()
    rows = []
    for row in data["questions"]:
        q = golden[row["id"]]
        row["expected"] = q["expected"]
        if "answer" in row:
            score_row(q, row, texts)
        rows.append(row)
    summary = summarize_generation(rows)
    print(f"recorregido: {args.rescore.name} (respuestas del {data['config']['date']}, sin volver a generar)")
    print_generation(summary, rows)
    if not args.no_save:
        out = args.rescore.with_name(args.rescore.stem + "_rescored.json")
        config = {**data["config"], "rescored_from": args.rescore.name, "rescore_commit": git_commit(),
                  "rescore_date": datetime.now().isoformat(timespec="seconds")}
        out.write_text(json.dumps({"config": config, "summary": summary, "questions": rows},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nguardado en {out.resolve().relative_to(ROOT)}")


def run_generation_stage(args, questions: list[dict], retriever) -> None:
    from rag_normainst.generate import DEFAULT_LLM
    from rag_normainst.pipeline import RAG

    llm = args.llm or DEFAULT_LLM
    if args.no_lookup:
        retriever.search_with_lookup = retriever.search   # el RAG usará solo la búsqueda semántica
    rag = RAG(llm=llm, k=MAIN_K, retriever=retriever)
    print(f"generación: {len(questions)} preguntas · LLM {llm} · k={MAIN_K} · embeddings {args.model}")
    t0 = time.perf_counter()
    rows = run_generation(questions, rag)
    print(f"tiempo total: {(time.perf_counter() - t0) / 60:.1f} min")
    summary = summarize_generation(rows)
    print_generation(summary, rows)
    if not args.no_save:
        save_result(args, "generation", summary, rows, {"llm": llm, "k": MAIN_K})


def main() -> None:
    parser = argparse.ArgumentParser(description="Evalúa la recuperación del RAG con el golden set.")
    parser.add_argument("--pipeline", choices=["pure"], default="pure",
                        help="qué implementación evaluar (langchain llegará en la Fase 2B)")
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--model", choices=sorted(MODELS), default=DEFAULT_MODEL)
    parser.add_argument("--no-lookup", action="store_true",
                        help="solo búsqueda semántica, sin buscar por id las IT/artículos citados")
    parser.add_argument("--stage", choices=["retrieval", "generation"], default="retrieval")
    parser.add_argument("--llm", default=None, help="modelo de Ollama (por defecto, el de generate.py)")
    parser.add_argument("--ids", default=None, help="solo estas preguntas, separadas por comas: q06,q37")
    parser.add_argument("--no-save", action="store_true", help="no guarda el resultado en eval/results/")
    parser.add_argument("--rescore", type=Path, default=None,
                        help="recorrige un resultado de generación guardado, sin LLM")
    args = parser.parse_args()
    if args.rescore:
        rescore(args)
        return

    from rag_normainst.retrieve import Retriever   # aquí: carga torch, que tarda

    questions = load_golden(args.golden)
    if args.ids:
        wanted = set(args.ids.split(","))
        questions = [q for q in questions if q["id"] in wanted]
    t0 = time.perf_counter()
    retriever = Retriever(args.model)
    t_load = time.perf_counter() - t0
    if args.stage == "generation":
        run_generation_stage(args, questions, retriever)
        return
    rows = run_retrieval(questions, retriever, lookup=not args.no_lookup)
    t_run = time.perf_counter() - t0 - t_load

    keys = metric_keys()
    answerable = [r for r in rows if r["expected"]]
    unanswerable = [r for r in rows if not r["expected"]]
    summary = {
        "total": aggregate(answerable, keys),
        "by_split": group_by(answerable, "split", keys),
        "by_type": group_by(answerable, "type", keys),
    }

    lookup_txt = "sin búsqueda por id" if args.no_lookup else "con búsqueda por id"
    print(f"golden set: {len(questions)} preguntas ({len(answerable)} con respuesta, "
          f"{len(unanswerable)} sin respuesta) · modelo {args.model} · {lookup_txt}")
    print(f"tiempos: carga {t_load:.1f} s · {len(questions)} búsquedas {t_run:.1f} s")
    print_table("TOTAL (preguntas con respuesta)", {"todas": summary["total"]})
    print_table("POR SPLIT", summary["by_split"])
    print_table("POR TIPO", summary["by_type"])

    fails = [r for r in answerable if r["rank"] is None or r["rank"] > MAIN_K]
    print(f"\nFALLOS con k={MAIN_K} (la unidad correcta no llega al LLM): {len(fails)}")
    for r in fails:
        print(f"  {r['id']} [{r['type']}] rango={r['rank']} · esperado {r['expected']}"
              f"\n      «{r['question']}»\n      top-3: {r['retrieved'][:3]}")
    partial = [r for r in answerable if r[f"hit@{MAIN_K}"] == 1 and r[f"recall@{MAIN_K}"] < 1]
    if partial:
        print(f"\nINCOMPLETAS con k={MAIN_K} (llega solo parte de lo esperado): "
              + ", ".join(f"{r['id']} ({r[f'recall@{MAIN_K}']:.2f})" for r in partial))

    # ¿Sirve la similitud del primer resultado para detectar «no consta»? (en la pieza 4: no)
    mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")
    s_ans = [r["top1_score"] for r in answerable]
    s_no = [r["top1_score"] for r in unanswerable]
    print(f"\nSIMILITUD DEL TOP-1: con respuesta media {mean(s_ans):.3f} (mín {min(s_ans):.3f})"
          f" · sin respuesta media {mean(s_no):.3f} (máx {max(s_no):.3f})")

    if not args.no_save:
        save_result(args, "retrieval", summary, rows, {"ks": list(KS), "main_k": MAIN_K})

if __name__ == "__main__":
    main()
