"""Pruebas del juez de fidelidad con un LLM falso."""

from __future__ import annotations

from types import SimpleNamespace

from rag_normainst.judge import build_judge_messages, judge, parse_verdict


class FakeClient:
    def __init__(self, text):
        self.text, self.sent = text, None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.sent = kw
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.text))])


HITS = [SimpleNamespace(unit="IT 1.2.4.7.4", title="Combustibles sólidos", page_start=54,
                        text="Queda prohibida la utilización de combustibles sólidos de origen fósil.")]


def test_el_juez_ve_los_fragmentos_numerados_y_la_respuesta():
    msgs = build_judge_messages("Está prohibido [1].", HITS)
    assert "[1] IT 1.2.4.7.4" in msgs[1]["content"] and "RESPUESTA\nEstá prohibido [1]." in msgs[1]["content"]


def test_lee_el_json_aunque_venga_con_texto_alrededor():
    v = parse_verdict('Claro: {"veredicto": "no_fiel", "afirmacion": "Sí, puedes", "motivo": "x"} fin')
    assert v.faithful is False and v.claim == "Sí, puedes"
    assert parse_verdict('{"veredicto": "fiel", "afirmacion": "", "motivo": ""}').faithful is True


def test_veredicto_ilegible_es_none():
    assert parse_verdict("no sé").faithful is None
    assert parse_verdict('{"veredicto": "quizá"}').faithful is None
    assert parse_verdict('{roto').faithful is None


def test_judge_con_temperatura_cero():
    client = FakeClient('{"veredicto": "fiel", "afirmacion": "", "motivo": "ok"}')
    v = judge("Está prohibido [1].", HITS, client, "juez-x")
    assert v.faithful is True and client.sent["temperature"] == 0 and client.sent["model"] == "juez-x"
