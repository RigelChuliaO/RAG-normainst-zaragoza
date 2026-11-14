"""Pruebas de store.py, con un modelo y un tokenizer falsos.

No descargan nada ni necesitan el modelo real: comprueban la lógica del índice
(red de seguridad, metadatos válidos, coseno, idempotencia). Necesitan chromadb;
si no está instalado, se saltan.
"""

from __future__ import annotations

import numpy as np
import pytest

chromadb = pytest.importorskip("chromadb")

from rag_normainst.embeddings import MODELS
from rag_normainst.store import build_index, check_window, chunk_metadata


class FakeTokenizer:
    """Un token por palabra más los dos especiales, como hace count_tokens."""

    def __call__(self, texts, add_special_tokens=True, truncation=False):
        return {"input_ids": [[0] * (len(t.split()) + 2) for t in texts]}


class FakeModel:
    """Vectores aleatorios pero deterministas, ya normalizados."""

    def encode(self, texts, **kwargs):
        rng = np.random.default_rng(len(texts))
        v = rng.normal(size=(len(texts), 768))
        return v / np.linalg.norm(v, axis=1, keepdims=True)


def _chunk(cid: str, words: int = 10, page=5) -> dict:
    return {
        "id": cid, "doc": "DOC", "version": "v1", "part": "RITE", "unit": "Artículo 1",
        "title": "Objeto", "path": ["Parte I", "Capítulo I"], "piece": 1, "pieces": 1,
        "page_start": page, "page_end": page, "has_table": False, "refs": ["RITE:art-2"],
        "n_words": words, "text": " ".join(["texto"] * words),
        "embed_text": "RITE › Parte I › Capítulo I › Artículo 1. Objeto\n" + " ".join(["texto"] * words),
    }


def test_red_de_seguridad_para_si_un_chunk_no_cabe():
    """Un chunk de 600 palabras no cabe en 512 tokens: debe parar, no truncar."""
    with pytest.raises(ValueError, match="superan la ventana"):
        check_window([_chunk("RITE:art-1", words=600)], MODELS["e5-base"], FakeTokenizer())


def test_metadatos_validos_para_chroma():
    """Chroma solo admite str, int, float o bool: ni None ni listas."""
    meta = chunk_metadata(_chunk("RITE:art-1", page=None))
    assert all(isinstance(v, (str, int, float, bool)) for v in meta.values())
    assert meta["page_start"] == -1
    assert meta["path"] == "Parte I › Capítulo I"
    assert meta["refs"] == "RITE:art-2"


def test_indice_con_coseno_modelo_guardado_e_idempotente(tmp_path):
    chunks = [_chunk(f"RITE:art-{i}") for i in range(1, 6)]
    col = build_index(chunks, "e5-base", FakeModel(), FakeTokenizer(), tmp_path)
    assert col.count() == 5
    assert col.metadata["model"] == MODELS["e5-base"].name     # para comprobarlo al buscar
    assert col.configuration["hnsw"]["space"] == "cosine"
    # Segunda ejecución: mismo resultado, sin duplicados.
    col = build_index(chunks, "e5-base", FakeModel(), FakeTokenizer(), tmp_path)
    assert col.count() == 5
    got = col.get(ids=["RITE:art-3"], include=["documents", "metadatas"])
    assert got["metadatas"][0]["unit"] == "Artículo 1"
