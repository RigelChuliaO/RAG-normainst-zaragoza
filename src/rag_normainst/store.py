"""Índice vectorial: chunks -> vectores (e5-base en CPU) -> Chroma en disco.

Qué hace build_index, en orden:
  1. Comprueba que ningún chunk supera la ventana del modelo (red de seguridad):
     si alguno no cabe, PARA con error en vez de dejar que se trunque en silencio.
  2. Calcula los vectores con el modelo elegido y su prefijo ("passage: " en E5).
  3. Guarda en Chroma, por cada chunk: id, vector, texto y metadatos para citar.

Decisiones que evitan los errores típicos:
  - Los vectores los calculamos nosotros y se los damos hechos a Chroma
    (embedding_function=None). Si no, Chroma usaría su propio modelo por defecto,
    pequeño y en inglés, sin avisar.
  - La colección mide distancia coseno, no la euclídea que trae por defecto.
  - Es idempotente: si la colección ya existe, se borra y se crea de nuevo, así
    que ejecutarlo varias veces da el mismo índice, sin duplicados.
  - El nombre del modelo queda guardado en la colección: al buscar se comprueba
    que la pregunta se convierte en vector con el MISMO modelo.

Uso (desde la raíz del repo, con el entorno activado). La primera vez descarga
el modelo (≈1,1 GB) de Hugging Face; después funciona sin conexión:
  python -m rag_normainst.store "data/processed/BOE-A-2007-15820-consolidado.chunks.jsonl"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from rag_normainst.embeddings import DEFAULT_MODEL, MODELS, ModelSpec, count_tokens, passage_input, query_input

DEFAULT_PERSIST_DIR = Path("chroma")


def collection_name(model_key: str) -> str:
    """Una colección por modelo: permite comparar modelos sin pisar índices."""
    return f"rite_{model_key}"


def load_chunks(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(raw) for raw in f]


def check_window(chunks: list[dict], spec: ModelSpec, tokenizer) -> None:
    """Red de seguridad: para si algún chunk no cabe en la ventana del modelo."""
    lengths = count_tokens([passage_input(c, spec) for c in chunks], tokenizer)
    over = [(c["id"], n) for c, n in zip(chunks, lengths) if n > spec.max_tokens]
    if over:
        raise ValueError(
            f"{len(over)} chunks superan la ventana de {spec.max_tokens} tokens de "
            f"{spec.name} y se truncarían: {over[:5]}. Baja MAX_WORDS en chunk.py."
        )


def chunk_metadata(chunk: dict) -> dict:
    """Metadatos que guarda Chroma: solo str, int, float o bool, nunca None."""
    meta = {
        "doc": chunk["doc"],
        "version": chunk.get("version") or "",
        "part": chunk["part"],
        "unit": chunk["unit"],
        "title": chunk["title"],
        "path": " › ".join(chunk["path"]),
        "piece": chunk["piece"],
        "pieces": chunk["pieces"],
        "page_start": chunk["page_start"] if chunk["page_start"] is not None else -1,
        "page_end": chunk["page_end"] if chunk["page_end"] is not None else -1,
        "has_table": bool(chunk["has_table"]),
        "refs": ",".join(chunk["refs"]),
        "n_words": chunk["n_words"],
    }
    return meta


def embed_passages(chunks: list[dict], spec: ModelSpec, model, batch_size: int = 16) -> list[list[float]]:
    """Vectores normalizados (longitud 1) de los chunks, con el prefijo del modelo."""
    vectors = model.encode(
        [passage_input(c, spec) for c in chunks],
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    return [v.tolist() for v in vectors]


def build_index(chunks: list[dict], model_key: str, model, tokenizer,
                persist_dir: Path = DEFAULT_PERSIST_DIR, source_sha256: str = ""):
    """Crea (o recrea) la colección del modelo con todos los chunks."""
    import chromadb

    spec = MODELS[model_key]
    check_window(chunks, spec, tokenizer)
    vectors = embed_passages(chunks, spec, model)

    client = chromadb.PersistentClient(path=str(persist_dir))
    name = collection_name(model_key)
    if name in [c.name for c in client.list_collections()]:
        client.delete_collection(name)  # idempotente: siempre se parte de cero
    collection = client.create_collection(
        name=name,
        embedding_function=None,                     # los vectores los ponemos nosotros
        configuration={"hnsw": {"space": "cosine"}},  # distancia coseno
        metadata={"model": spec.name, "dim": spec.dim, "n_chunks": len(chunks),
                  "source_sha256": source_sha256},
    )
    collection.add(
        ids=[c["id"] for c in chunks],
        embeddings=vectors,
        documents=[c["text"] for c in chunks],
        metadatas=[chunk_metadata(c) for c in chunks],
    )
    return collection


def quick_check(collection, spec: ModelSpec, model, question: str, k: int = 3) -> None:
    """Prueba rápida al terminar: los k chunks más cercanos a una pregunta conocida."""
    qv = model.encode([query_input(question, spec)], normalize_embeddings=True)[0].tolist()
    res = collection.query(query_embeddings=[qv], n_results=k)
    print(f'\nprueba: "{question}"')
    for cid, dist, meta in zip(res["ids"][0], res["distances"][0], res["metadatas"][0]):
        print(f"  similitud {1 - dist:.3f} | {cid} | {meta['title'][:60]} (pág. {meta['page_start']})")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Indexa los chunks en Chroma.")
    parser.add_argument("chunks", type=Path, help="ruta al .chunks.jsonl de chunk.py")
    parser.add_argument("--model", choices=sorted(MODELS), default=DEFAULT_MODEL)
    parser.add_argument("--persist-dir", type=Path, default=DEFAULT_PERSIST_DIR)
    args = parser.parse_args()

    # Import aquí: sentence-transformers (y torch) tarda unos segundos en cargar.
    from sentence_transformers import SentenceTransformer

    spec = MODELS[args.model]
    chunks = load_chunks(args.chunks)
    print(f"cargando {spec.name} en CPU…")
    model = SentenceTransformer(spec.name, device="cpu")

    t0 = time.perf_counter()
    collection = build_index(chunks, args.model, model, model.tokenizer,
                             args.persist_dir, file_sha256(args.chunks))
    print(f"indexados {collection.count()} chunks en '{collection.name}' "
          f"({args.persist_dir}/) en {time.perf_counter() - t0:.0f} s")
    quick_check(collection, spec, model, "¿Qué temperatura operativa se exige en invierno?")


if __name__ == "__main__":
    main()
