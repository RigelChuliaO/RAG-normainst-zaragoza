"""Métricas de evaluación de la recuperación (Fase 2).

Todo son funciones puras: reciben listas de ids y devuelven números. No cargan
modelos ni índices, así que se prueban en milisegundos (tests/test_metrics.py).

Regla de comparación: POR UNIDAD, no por chunk. El golden set dice
"RITE:IT-3.8" y acierta cualquier chunk de esa unidad ("RITE:IT-3.8#2"...).
Así el golden set sigue valiendo aunque cambie el tamaño de los chunks.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path


def unit_of(chunk_id: str) -> str:
    """Id de la unidad a la que pertenece un chunk: "RITE:IT-3.8#2" -> "RITE:IT-3.8"."""
    return chunk_id.split("#")[0]


def first_hit_rank(retrieved: list[str], expected: list[str]) -> int | None:
    """Posición (1, 2, 3...) del primer chunk recuperado que es de una unidad esperada.

    None si ninguno lo es. Las posiciones cuentan chunks, como el k del RAG.
    """
    wanted = set(expected)
    for pos, cid in enumerate(retrieved, start=1):
        if unit_of(cid) in wanted:
            return pos
    return None


def hit_at_k(retrieved: list[str], expected: list[str], k: int) -> float:
    """1 si hay AL MENOS una unidad esperada entre los k primeros; si no, 0."""
    rank = first_hit_rank(retrieved, expected)
    return 1.0 if rank is not None and rank <= k else 0.0


def recall_at_k(retrieved: list[str], expected: list[str], k: int) -> float:
    """Fracción de las unidades esperadas que aparecen entre los k primeros.

    Solo se diferencia de hit@k cuando hay varias correctas (p. ej. q06: la
    IT 1.1.4.1.2 Y la IT 3.8). Si llega una de dos, hit@k = 1 pero recall@k = 0,5.
    """
    found = {unit_of(c) for c in retrieved[:k]}
    return len(found & set(expected)) / len(expected)


def reciprocal_rank(retrieved: list[str], expected: list[str]) -> float:
    """1 / posición del primer acierto (0 si no hay). La media sobre preguntas es la MRR."""
    rank = first_hit_rank(retrieved, expected)
    return 1.0 / rank if rank else 0.0


def load_golden(path: Path) -> list[dict]:
    """Lee el golden set (una pregunta por línea, JSONL)."""
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def score_retrieval(question: dict, retrieved: list[str], ks: tuple[int, ...]) -> dict:
    """Métricas de una pregunta CON respuesta. Las sin respuesta no entran aquí."""
    exp = question["expected"]
    row = {"rank": first_hit_rank(retrieved, exp), "rr": reciprocal_rank(retrieved, exp)}
    for k in ks:
        row[f"hit@{k}"] = hit_at_k(retrieved, exp, k)
        row[f"recall@{k}"] = recall_at_k(retrieved, exp, k)
    return row


def aggregate(rows: list[dict], keys: list[str]) -> dict:
    """Media de cada métrica sobre un grupo de preguntas (n = cuántas)."""
    out = {"n": len(rows)}
    for key in keys:
        out[key] = sum(r[key] for r in rows) / len(rows) if rows else 0.0
    return out


def group_by(rows: list[dict], field: str, keys: list[str]) -> dict[str, dict]:
    """Medias por valor de un campo ("type", "split"...): el desglose de errores."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r[field]].append(r)
    return {name: aggregate(g, keys) for name, g in sorted(groups.items())}


# ---------------------------------------------------------------------------
# Generación: corrección hecha por CÓDIGO (sin LLM). Determinista y gratis.
# Lo que el código no puede juzgar (la fidelidad completa) lo hará el juez LLM.
# ---------------------------------------------------------------------------

NUMBER_DOT_RE = re.compile(r"(\d)\.(\d)")


def normalize(text: str) -> str:
    """Texto comparable: minúsculas, espacios simples, º -> °, y 12.5 -> 12,5.

    El RITE escribe los decimales con coma; si el modelo escribe "12.5", el dato
    es el mismo y no debe contar como fallo.
    """
    text = text.replace(" ", " ").replace("º", "°").lower()
    text = NUMBER_DOT_RE.sub(r"\1,\2", text)
    return re.sub(r"\s+", " ", text).strip()


def coverage(text: str, must: list) -> float:
    """Fracción de los datos obligatorios que aparecen en la respuesta (1 si no hay).

    Cada dato puede ser un texto o una lista de alternativas válidas:
    ["calidad media", "buena calidad"] se cumple si aparece cualquiera de las dos.
    """
    if not must:
        return 1.0
    t = normalize(text)
    present = lambda m: any(normalize(x) in t for x in m) if isinstance(m, list) else normalize(m) in t
    return sum(present(m) for m in must) / len(must)


def forbidden_found(text: str, must_not: list[str]) -> list[str]:
    """Datos prohibidos que SÍ aparecen (p. ej. "60 °C" en la legionela): invención."""
    t = normalize(text)
    return [m for m in must_not if normalize(m) in t]


def abstention_outcome(expected: list[str], said_no_consta: bool) -> str:
    """Las cuatro casillas de «no consta» (como un detector de humo).

    - responde_bien_consta:   había respuesta y respondió (aún falta ver si bien)
    - no_consta_correcto:     no había respuesta y dijo «No consta»
    - no_consta_indebido:     había respuesta y se calló      (error leve)
    - inventa:                no había respuesta y respondió  (error grave)
    """
    answerable = bool(expected)
    if answerable:
        return "no_consta_indebido" if said_no_consta else "responde_cuando_consta"
    return "no_consta_correcto" if said_no_consta else "inventa"


def score_generation(question: dict, text: str, said_no_consta: bool, cited_ids: list[str],
                     invalid_labels: list[int], retrieved: list[str], context: str | None = None,
                     mixed_no_consta: bool = False) -> dict:
    """Corrección de una respuesta y diagnóstico de dónde falló.

    `correct` (correcta según el código):
      - con respuesta: no dice «No consta», contiene todos los must_contain
        y ninguno de los must_not_contain;
      - sin respuesta: dice «No consta».
    `complete`: correcta y, además, cita TODAS las unidades esperadas.
    `diagnosis`: "ok", "fallo_recuperacion" (los datos no llegaron al LLM: no es
    culpa del modelo) o "fallo_generacion" (le llegaron y respondió mal).

    Si se pasa `context` (el texto de los chunks recuperados), el diagnóstico mira
    si los DATOS obligatorios estaban en él. Es más fino que mirar la unidad: una
    unidad larga (IT 3.3, 6 trozos) puede llegar sin el trozo que tiene la tabla.
    """
    expected = question["expected"]
    must, must_not = question.get("must_contain", []), question.get("must_not_contain", [])
    outcome = abstention_outcome(expected, said_no_consta)
    cited_units = {unit_of(c) for c in cited_ids}
    row = {
        "abstention": outcome,
        "coverage": coverage(text, must) if expected else None,
        "forbidden": forbidden_found(text, must_not),
        "n_citations": len(cited_ids),
        "invalid_labels": invalid_labels,
        "cites_expected": bool(cited_units & set(expected)) if expected else None,
        # Recall de citas: qué parte de las unidades esperadas cita la respuesta.
        # Detecta la incompletitud que los números no ven (q06: IT 3.8 también dice 21 °C).
        "citation_recall": len(cited_units & set(expected)) / len(expected) if expected else None,
        "context_hit": first_hit_rank(retrieved, expected) is not None if expected else None,
        "context_coverage": coverage(context, must) if expected and context is not None else None,
        "mixed_no_consta": mixed_no_consta,
    }
    if expected:
        row["correct"] = (not said_no_consta and row["coverage"] == 1.0 and not row["forbidden"])
    else:
        row["correct"] = said_no_consta
    # Completa = correcta Y cita todas las unidades esperadas (más exigente).
    row["complete"] = row["correct"] and (not expected or row["citation_recall"] == 1.0)
    if row["correct"]:
        row["diagnosis"] = "ok"
    elif expected and (not row["context_hit"] or (context is not None and row["context_coverage"] < 1.0)):
        # Fallo de recuperación si no llegó la unidad, o llegó sin el trozo con los datos.
        row["diagnosis"] = "fallo_recuperacion"
    else:
        row["diagnosis"] = "fallo_generacion"
    return row
