"""answer(pregunta) -> Answer: la tubería completa del RAG.

  1. Recuperación: los k chunks más parecidos (retrieve.py). Si la pregunta cita
     una unidad concreta ("IT 1.2.4.7.4", "artículo 18"), ese chunk se busca por
     id y va primero: la búsqueda semántica no entiende de códigos.
  2. Generación: el LLM responde solo con esos chunks y cita con [n] (generate.py).

Esta es la interfaz que usará la evaluación de la Fase 2 (y el port a LangChain
de la Fase 2B): recibe una pregunta y devuelve texto, citas e ids recuperados.

Uso (con Ollama en marcha y el entorno activado):
  python -m rag_normainst.pipeline "¿Qué temperatura operativa se exige en invierno?"
  python -m rag_normainst.pipeline "¿Qué dice la IT 1.2.4.7.4?" --llm qwen3:1.7b
"""

from __future__ import annotations

import argparse
import time

from rag_normainst.generate import DEFAULT_LLM, Answer, generate, make_client
from rag_normainst.retrieve import Retriever


class RAG:
    """Mantiene cargados el índice, el modelo de embeddings y el cliente del LLM."""

    def __init__(self, llm: str = DEFAULT_LLM, k: int = 5, retriever=None, client=None):
        self.retriever = retriever or Retriever()
        self.client = client or make_client()
        self.llm = llm
        self.k = k

    def answer(self, question: str) -> Answer:
        t0 = time.perf_counter()
        hits = self.retriever.search_with_lookup(question, self.k)
        seconds_retrieve = time.perf_counter() - t0
        result = generate(question, hits, self.client, self.llm)
        result.seconds_retrieve = seconds_retrieve
        return result


def print_answer(a: Answer) -> None:
    print(f'\npregunta: "{a.question}"\n')
    print(a.text)
    if a.citations:
        print("\nfuentes:")
        for c in a.citations:
            print(f"  {c}")
    if a.invalid_labels:
        print(f"\nALERTA: el modelo citó fragmentos que no existen: {a.invalid_labels}")
    if not a.citations and not a.no_consta:
        print("\nALERTA: respuesta sin ninguna cita")
    print(f"\nrecuperados: {', '.join(a.retrieved_ids)}")
    print(f"tiempos: recuperación {a.seconds_retrieve:.1f} s · generación {a.seconds_generate:.1f} s"
          f" · tokens del prompt {a.prompt_tokens} · de la respuesta {a.completion_tokens}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Responde una pregunta sobre el RITE citando el artículo.")
    parser.add_argument("question")
    parser.add_argument("-k", type=int, default=5)
    parser.add_argument("--llm", default=DEFAULT_LLM, help="modelo de Ollama")
    args = parser.parse_args()
    rag = RAG(llm=args.llm, k=args.k)
    print_answer(rag.answer(args.question))


if __name__ == "__main__":
    main()
