"""Pruebas de retrieve.py con un modelo falso (no descargan nada)."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("chromadb")

from rag_normainst.retrieve import Retriever
from rag_normainst.store import build_index


class FakeTokenizer:
    def __call__(self, texts, add_special_tokens=True, truncation=False):
        return {"input_ids": [[0] * (len(t.split()) + 2) for t in texts]}


class FakeModel:
    """Vector determinista por texto (semilla = hash del texto), normalizado."""

    def encode(self, texts, **kwargs):
        out = []
        for t in texts:
            rng = np.random.default_rng(abs(hash(t)) % (2**32))
            v = rng.normal(size=768)
            out.append(v / np.linalg.norm(v))
        return np.asarray(out)


def _chunks(n: int) -> list[dict]:
    return [{
        "id": f"RITE:art-{i}", "doc": "DOC", "version": "v1", "part": "RITE",
        "unit": f"Artículo {i}", "title": f"Título {i}", "path": ["Parte I"], "piece": 1, "pieces": 1,
        "page_start": i, "page_end": i, "has_table": False, "refs": [], "n_words": 3,
        "text": f"texto del artículo {i}", "embed_text": f"Parte I › Artículo {i}\ntexto del artículo {i}",
    } for i in range(1, n + 1)]


def test_chroma_y_numpy_dan_el_mismo_resultado(tmp_path):
    build_index(_chunks(30), "e5-base", FakeModel(), FakeTokenizer(), tmp_path)
    r = Retriever("e5-base", tmp_path, model=FakeModel())
    for q in ["pregunta uno", "otra pregunta distinta"]:
        a, b = r.search(q, 5), r.search_numpy(q, 5)
        assert [h.id for h in a] == [h.id for h in b]
        assert all(abs(x.score - y.score) < 1e-4 for x, y in zip(a, b))
        assert [h.score for h in a] == sorted([h.score for h in a], reverse=True)


def test_para_si_el_indice_es_de_otro_modelo(tmp_path):
    build_index(_chunks(5), "e5-small", FakeModel(), FakeTokenizer(), tmp_path)
    col = __import__("chromadb").PersistentClient(path=str(tmp_path)).get_collection("rite_e5-small")
    col.modify(metadata={**col.metadata, "model": "otro/modelo"})
    with pytest.raises(ValueError, match="reindexa"):
        Retriever("e5-small", tmp_path, model=FakeModel())
