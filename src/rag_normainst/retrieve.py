"""Recuperación: pregunta -> los k chunks más parecidos del índice.

Dos formas de buscar, que deben dar EXACTAMENTE el mismo resultado:
  - search():        se lo pide a Chroma (lo que se usará en el RAG).
  - search_numpy():  lo mismo hecho a mano con NumPy, para ver que una base
                     vectorial no hace magia: es un producto escalar y una ordenación.

Por qué el producto escalar basta: los vectores están normalizados (longitud 1),
y para vectores de longitud 1 el coseno del ángulo ES el producto escalar.

Uso (desde la raíz del repo, con el entorno activado):
  python -m rag_normainst.retrieve "¿Qué temperatura operativa se exige en invierno?"
  python -m rag_normainst.retrieve "¿Cada cuánto se revisa una caldera?" -k 5 --compare
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from rag_normainst.embeddings import DEFAULT_MODEL, MODELS, query_input
from rag_normainst.store import DEFAULT_PERSIST_DIR, collection_name


@dataclass
class Hit:
    """Un resultado de la búsqueda: el chunk y lo parecido que es a la pregunta."""
    id: str
    score: float      # similitud coseno (1 = idéntico)
    unit: str         # "Artículo 2", "IT 1.1.4.1.2"... (para citar)
    title: str
    page_start: int
    text: str


class Retriever:
    """Carga el índice de un modelo y busca en él."""

    def __init__(self, model_key: str = DEFAULT_MODEL, persist_dir: Path = DEFAULT_PERSIST_DIR, model=None):
        import chromadb

        self.spec = MODELS[model_key]
        client = chromadb.PersistentClient(path=str(persist_dir))
        self.collection = client.get_collection(collection_name(model_key))
        # Error típico: buscar con un modelo distinto del que indexó.
        indexed_with = self.collection.metadata.get("model")
        if indexed_with != self.spec.name:
            raise ValueError(f"el índice se creó con {indexed_with}, no con {self.spec.name}: reindexa")
        if model is None:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(self.spec.name, device="cpu")
        self.model = model
        self._matrix = None  # caché para search_numpy

    def embed_query(self, question: str) -> np.ndarray:
        """Vector normalizado de la pregunta, con el prefijo de pregunta del modelo."""
        return np.asarray(self.model.encode([query_input(question, self.spec)], normalize_embeddings=True)[0])

    def search(self, question: str, k: int = 5) -> list[Hit]:
        """Los k chunks más parecidos, según Chroma."""
        qv = self.embed_query(question)
        res = self.collection.query(query_embeddings=[qv.tolist()], n_results=k,
                                    include=["documents", "metadatas", "distances"])
        return [
            Hit(cid, 1 - dist, meta["unit"], meta["title"], meta["page_start"], doc)
            for cid, dist, meta, doc in zip(res["ids"][0], res["distances"][0],
                                            res["metadatas"][0], res["documents"][0])
        ]

    def lookup_units(self, units: list[str]) -> list[Hit]:
        """Chunks de las unidades citadas, buscados por metadato (no por similitud)."""
        hits: list[Hit] = []
        for unit in units:
            got = self.collection.get(where={"unit": unit}, include=["documents", "metadatas"])
            for cid, meta, doc in sorted(zip(got["ids"], got["metadatas"], got["documents"]),
                                         key=lambda x: x[1]["piece"]):
                hits.append(Hit(cid, 1.0, meta["unit"], meta["title"], meta["page_start"], doc))
        return hits

    def search_with_lookup(self, question: str, k: int = 5) -> list[Hit]:
        """Primero las unidades citadas por id; después, la búsqueda semántica."""
        exact = self.lookup_units(cited_units(question))
        seen = {h.id for h in exact}
        semantic = [h for h in self.search(question, k) if h.id not in seen]
        return (exact + semantic)[:max(k, len(exact))]

    def search_numpy(self, question: str, k: int = 5) -> list[Hit]:
        """Lo mismo que search(), a mano: producto escalar contra todos y ordenar."""
        if self._matrix is None:
            # Se leen de Chroma todos los vectores guardados: matriz de 417 × 768.
            data = self.collection.get(include=["embeddings", "documents", "metadatas"])
            self._ids, self._docs, self._metas = data["ids"], data["documents"], data["metadatas"]
            self._matrix = np.asarray(data["embeddings"])
        qv = self.embed_query(question)
        scores = self._matrix @ qv               # 417 similitudes coseno de una vez
        best = np.argsort(-scores)[:k]           # índices de las k mayores, de mayor a menor
        return [
            Hit(self._ids[i], float(scores[i]), self._metas[i]["unit"], self._metas[i]["title"],
                self._metas[i]["page_start"], self._docs[i])
            for i in best
        ]


# Unidades citadas en la pregunta: "IT 1.2.4.7.4", "artículo 18".
CITED_IT_RE = re.compile(r"\bIT\s+(\d+(?:\.\d+)+)")
CITED_ART_RE = re.compile(r"\bart[íi]culo\s+(\d+)\b", re.IGNORECASE)


def cited_units(question: str) -> list[str]:
    """Etiquetas de unidad ("IT 1.2.4.7.4", "Artículo 18") que nombra la pregunta."""
    units = [f"IT {n.rstrip('.')}" for n in CITED_IT_RE.findall(question)]
    units += [f"Artículo {n}" for n in CITED_ART_RE.findall(question)]
    return units


def print_hits(hits: list[Hit], label: str) -> None:
    print(f"\n{label}")
    for n, h in enumerate(hits, start=1):
        print(f"  {n}. {h.score:.3f} | {h.id} | {h.title[:55]} (pág. {h.page_start})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Busca los chunks más parecidos a una pregunta.")
    parser.add_argument("question")
    parser.add_argument("-k", type=int, default=5)
    parser.add_argument("--model", choices=sorted(MODELS), default=DEFAULT_MODEL)
    parser.add_argument("--compare", action="store_true", help="compara Chroma con NumPy a mano")
    parser.add_argument("--show-text", action="store_true", help="muestra el texto del primer resultado")
    args = parser.parse_args()

    retriever = Retriever(args.model)
    hits = retriever.search(args.question, args.k)
    print(f'pregunta: "{args.question}"')
    print_hits(hits, "Chroma:")
    if args.compare:
        manual = retriever.search_numpy(args.question, args.k)
        print_hits(manual, "NumPy a mano:")
        same = [h.id for h in hits] == [m.id for m in manual]
        diff = max(abs(h.score - m.score) for h, m in zip(hits, manual))
        print(f"\n¿mismo orden? {'sí' if same else 'NO'} · diferencia máxima de puntuación: {diff:.6f}")
    if args.show_text and hits:
        print(f"\ntexto de {hits[0].id}:\n{hits[0].text}")


if __name__ == "__main__":
    main()
