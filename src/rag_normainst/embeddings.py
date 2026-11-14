"""Modelos de embeddings: configuración y medida de los chunks en tokens.

Este módulo reúne en un solo sitio lo que cambia de un modelo de embeddings a
otro (nombre, prefijos, ventana) para que el resto del código no tenga que
saberlo. De momento ofrece una utilidad: MEDIR los chunks en tokens reales del
modelo, para comprobar que ninguno supera su ventana (si la supera, el modelo
corta el final sin avisar).

Modelos candidatos (ADR-006). Datos comprobados en sus fichas de Hugging Face:
  - e5-base  · intfloat/multilingual-e5-base · 768 dim. · 512 tokens · prefijos
  - e5-small · intfloat/multilingual-e5-small · 384 dim. · 512 tokens · prefijos
  - bge-m3   · BAAI/bge-m3 · 1024 dim. · 8192 tokens · sin prefijos

Los modelos E5 se entrenaron con "query: " delante de las preguntas y
"passage: " delante de los textos: sin ellos funcionan peor, sin avisar.

Uso (desde la raíz del repo, con el entorno activado). La primera vez descarga
el tokenizer del modelo desde Hugging Face (unos MB, a la caché del usuario):
  python -m rag_normainst.embeddings "data/processed/BOE-A-2007-15820-consolidado.chunks.jsonl"
  python -m rag_normainst.embeddings "data/processed/....chunks.jsonl" --model bge-m3
"""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelSpec:
    """Lo que distingue a un modelo de embeddings a efectos de este proyecto."""
    name: str            # identificador en Hugging Face
    query_prefix: str    # se antepone a la pregunta
    passage_prefix: str  # se antepone a cada chunk al indexar
    max_tokens: int      # ventana: lo que pase de aquí se trunca
    dim: int             # dimensiones del vector


MODELS: dict[str, ModelSpec] = {
    "e5-base": ModelSpec("intfloat/multilingual-e5-base", "query: ", "passage: ", 512, 768),
    "e5-small": ModelSpec("intfloat/multilingual-e5-small", "query: ", "passage: ", 512, 384),
    "bge-m3": ModelSpec("BAAI/bge-m3", "", "", 8192, 1024),
}
DEFAULT_MODEL = "e5-base"


def passage_input(chunk: dict, spec: ModelSpec) -> str:
    """Texto exacto que recibe el modelo al indexar un chunk: prefijo + ruta + cuerpo."""
    return spec.passage_prefix + chunk["embed_text"]


def query_input(question: str, spec: ModelSpec) -> str:
    """Texto exacto que recibe el modelo al convertir una pregunta en vector."""
    return spec.query_prefix + question


def count_tokens(texts: list[str], tokenizer) -> list[int]:
    """Tokens de cada texto, contando los especiales (<s>, </s>) y SIN truncar.

    Sin truncar es la clave: queremos ver la longitud real, no la que el modelo
    acabaría leyendo.
    """
    encoded = tokenizer(texts, add_special_tokens=True, truncation=False)
    return [len(ids) for ids in encoded["input_ids"]]


def measure(chunks: list[dict], spec: ModelSpec, tokenizer) -> dict:
    """Estadísticas de longitud de los chunks en tokens del modelo."""
    full = count_tokens([passage_input(c, spec) for c in chunks], tokenizer)
    body = count_tokens([c["text"] for c in chunks], tokenizer)
    words = [c["n_words"] for c in chunks]
    over = sorted(
        ((c["id"], t, c["n_words"]) for c, t in zip(chunks, full) if t > spec.max_tokens),
        key=lambda x: -x[1],
    )
    ordered = sorted(full)
    return {
        "model": spec.name,
        "max_tokens": spec.max_tokens,
        "n_chunks": len(chunks),
        "tokens_median": statistics.median(full),
        "tokens_p95": ordered[int(0.95 * (len(ordered) - 1))],
        "tokens_max": max(full),
        "tokens_per_word": round(sum(body) / max(1, sum(words)), 2),
        # Lo que añaden el prefijo del modelo y la ruta de títulos (embed_text - text).
        "prefix_tokens_median": statistics.median(f - b for f, b in zip(full, body)),
        "prefix_tokens_max": max(f - b for f, b in zip(full, body)),
        "n_over_window": len(over),
        "over_window": over,
    }


def print_report(r: dict) -> None:
    print(f"modelo: {r['model']}  ·  ventana: {r['max_tokens']} tokens  ·  chunks: {r['n_chunks']}")
    print(f"tokens por chunk (prefijo + ruta + cuerpo): mediana {r['tokens_median']}, "
          f"p95 {r['tokens_p95']}, máx {r['tokens_max']}")
    print(f"tokens por palabra del cuerpo: {r['tokens_per_word']}")
    print(f"tokens que añaden prefijo y ruta: mediana {r['prefix_tokens_median']}, máx {r['prefix_tokens_max']}")
    print(f"chunks que SUPERAN la ventana (se truncarían): {r['n_over_window']}")
    for cid, tokens, words in r["over_window"][:15]:
        print(f"  {cid}: {tokens} tokens ({words} palabras)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mide los chunks en tokens del modelo de embeddings.")
    parser.add_argument("chunks", type=Path, help="ruta al .chunks.jsonl de chunk.py")
    parser.add_argument("--model", choices=sorted(MODELS), default=DEFAULT_MODEL)
    args = parser.parse_args()

    # Import aquí: transformers tarda en cargar y solo hace falta al medir.
    from transformers import AutoTokenizer

    spec = MODELS[args.model]
    tokenizer = AutoTokenizer.from_pretrained(spec.name)
    with args.chunks.open(encoding="utf-8") as f:
        chunks = [json.loads(raw) for raw in f]
    print_report(measure(chunks, spec, tokenizer))


if __name__ == "__main__":
    main()
