"""Pruebas de generate.py, pipeline.py y la búsqueda por unidad citada.

Usan un cliente de LLM falso: no necesitan Ollama ni descargan nada.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from rag_normainst.generate import (
    NO_CONSTA,
    NUM_CTX,
    build_messages,
    generate,
    parse_citations,
    strip_thinking,
)
from rag_normainst.pipeline import RAG
from rag_normainst.retrieve import Hit, cited_units


def _hits(n: int = 3) -> list[Hit]:
    return [Hit(f"RITE:IT-1.{i}", 0.8, f"IT 1.{i}", f"Título {i}", 20 + i, f"texto {i}") for i in range(1, n + 1)]


class FakeClient:
    """Imita client.chat.completions.create y guarda los mensajes recibidos."""

    def __init__(self, reply: str, prompt_tokens: int = 500):
        self.reply, self.prompt_tokens, self.sent = reply, prompt_tokens, None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, model, messages, temperature):
        self.sent = {"model": model, "messages": messages, "temperature": temperature}
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.reply))],
            usage=SimpleNamespace(prompt_tokens=self.prompt_tokens, completion_tokens=20),
        )


def test_el_prompt_numera_los_fragmentos_y_explica_el_no_consta():
    system, user = build_messages("¿Pregunta?", _hits(2))
    assert NO_CONSTA in system["content"]
    assert "[1] IT 1.1. Título 1 (pág. 21)" in user["content"]
    assert "[2] IT 1.2. Título 2 (pág. 22)" in user["content"]
    assert user["content"].endswith("PREGUNTA\n¿Pregunta?")


def test_las_citas_salen_de_los_metadatos_y_las_inventadas_se_detectan():
    citations, invalid = parse_citations("Es así [1] y también [3]. Además [7].", _hits(3))
    assert [c.id for c in citations] == ["RITE:IT-1.1", "RITE:IT-1.3"]
    assert str(citations[0]) == "[1] RITE, IT 1.1. Título 1 (pág. 21)"
    assert invalid == [7]


def test_se_quita_el_razonamiento_si_el_modelo_lo_emite():
    assert strip_thinking("bla bla razonando</think>\n\nRespuesta [1].") == "Respuesta [1]."
    assert strip_thinking("Respuesta directa [2].") == "Respuesta directa [2]."


def test_generate_con_temperatura_cero_y_citas():
    client = FakeClient("La temperatura operativa es 21...23 ºC [1].")
    a = generate("¿Temperatura en invierno?", _hits(3), client, "modelo-x")
    assert client.sent["temperature"] == 0
    assert a.citations[0].unit == "IT 1.1"
    assert a.retrieved_ids == ["RITE:IT-1.1", "RITE:IT-1.2", "RITE:IT-1.3"]
    assert not a.no_consta and not a.invalid_labels


def test_detecta_el_no_consta():
    a = generate("¿Sección de cable?", _hits(3), FakeClient(NO_CONSTA))
    assert a.no_consta and not a.mixed_no_consta and a.citations == []


def test_respuesta_mixta_no_cuenta_como_no_consta():
    # Caso real (q25): responde bien y añade la frase al final
    a = generate("¿Contrato?", _hits(3), FakeClient("Si supera 70 kW [1].\n\nNo consta en el RITE."))
    assert not a.no_consta and a.mixed_no_consta


def test_para_si_el_prompt_llena_la_ventana():
    """Si el prompt llena el contexto, Ollama lo habrá recortado: mejor fallar alto."""
    with pytest.raises(RuntimeError, match="truncado"):
        generate("¿?", _hits(3), FakeClient("x [1]", prompt_tokens=NUM_CTX))


def test_detecta_unidades_citadas_en_la_pregunta():
    assert cited_units("¿Qué dice la IT 1.2.4.7.4?") == ["IT 1.2.4.7.4"]
    assert cited_units("¿Y el artículo 18 del RITE?") == ["Artículo 18"]
    assert cited_units("¿Qué temperatura en invierno?") == []


def test_pipeline_pone_primero_la_unidad_citada(tmp_path):
    pytest.importorskip("chromadb")
    from rag_normainst.retrieve import Retriever
    from rag_normainst.store import build_index

    class Tok:
        def __call__(self, texts, **kw):
            return {"input_ids": [[0] * (len(t.split()) + 2) for t in texts]}

    class Model:
        def encode(self, texts, **kw):
            rng = np.random.default_rng(len(texts[0]))
            v = rng.normal(size=(len(texts), 768))
            return v / np.linalg.norm(v, axis=1, keepdims=True)

    chunks = [{
        "id": f"RITE:IT-1.2.4.7.{i}", "doc": "D", "version": "v", "part": "RITE",
        "unit": f"IT 1.2.4.7.{i}", "title": f"T{i}", "path": [], "piece": 1, "pieces": 1,
        "page_start": 50, "page_end": 50, "has_table": False, "refs": [], "n_words": 2,
        "text": f"texto {i}", "embed_text": f"texto {i}",
    } for i in range(1, 6)]
    build_index(chunks, "e5-base", Model(), Tok(), tmp_path)
    rag = RAG(llm="m", k=3, retriever=Retriever("e5-base", tmp_path, model=Model()),
              client=FakeClient("Queda prohibido [1]."))
    a = rag.answer("¿Qué dice la IT 1.2.4.7.4?")
    assert a.retrieved_ids[0] == "RITE:IT-1.2.4.7.4"
    assert a.citations[0].unit == "IT 1.2.4.7.4"
    assert len(a.retrieved_ids) == 3
