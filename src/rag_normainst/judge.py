"""LLM como juez de la FIDELIDAD (Fase 2).

Pregunta que responde: ¿todo lo que afirma la respuesta está en los fragmentos
que recibió el modelo? No mira el solucionario (eso lo corrige el código en
metrics.py): una respuesta puede ser fiel e incompleta, o correcta por casualidad
e infiel (si acierta con conocimiento propio, no con los fragmentos).

Diseño pensado para un juez pequeño (qwen3 de 4B):
  - una sola pregunta cerrada por respuesta, no una afirmación por llamada;
  - salida en JSON y temperatura 0, para leerla con código y repetirla;
  - las respuestas que son solo «No consta» no se juzgan: no afirman nada.

Un juez así se equivoca: antes de usar su nota hay que CALIBRARLO contra el
criterio de una persona (eval/calibrate.py).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from rag_normainst.generate import DEFAULT_LLM, format_context

JUDGE_PROMPT = """Eres un revisor estricto. Recibes unos FRAGMENTOS de un reglamento y una RESPUESTA escrita a partir de ellos.

Tu tarea: decidir si TODAS las afirmaciones de la RESPUESTA están respaldadas por los FRAGMENTOS.

- "fiel": cada afirmación (datos, cifras, condiciones, sí/no) aparece en los fragmentos o se deduce directamente de ellos.
- "no_fiel": hay al menos una afirmación que NO está en los fragmentos, los contradice, o los aplica a un caso del que no hablan.
- Una respuesta incompleta pero sin nada inventado es "fiel".
- Las marcas [1], [2]... indican qué fragmento se cita; no las juzgues por sí solas.
- No uses tus propios conocimientos: solo los fragmentos.

Responde SOLO con un objeto JSON, sin texto antes ni después:
{"veredicto": "fiel" o "no_fiel", "afirmacion": "la primera afirmación no respaldada, copiada de la respuesta, o vacío si es fiel", "motivo": "una frase"}"""

JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class Verdict:
    faithful: bool | None        # None = el juez no dio un veredicto legible
    claim: str = ""              # afirmación no respaldada que señala
    reason: str = ""
    raw: str = ""                # texto tal cual, para revisar al juez


def build_judge_messages(answer: str, hits) -> list[dict]:
    """Mismos fragmentos que vio el modelo (con su numeración) + la respuesta."""
    user = f"FRAGMENTOS\n\n{format_context(hits)}\n\nRESPUESTA\n{answer}"
    return [{"role": "system", "content": JUDGE_PROMPT}, {"role": "user", "content": user}]


def parse_verdict(text: str) -> Verdict:
    """Lee el JSON del juez aunque venga con texto alrededor; si no se entiende, None."""
    m = JSON_RE.search(text or "")
    if not m:
        return Verdict(None, raw=text)
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return Verdict(None, raw=text)
    v = str(data.get("veredicto", "")).strip().lower().replace(" ", "_")
    faithful = True if v == "fiel" else False if v in ("no_fiel", "nofiel") else None
    return Verdict(faithful, str(data.get("afirmacion", "")), str(data.get("motivo", "")), text)


def judge(answer: str, hits, client, model: str = DEFAULT_LLM) -> Verdict:
    """Pide el veredicto de fidelidad de una respuesta."""
    response = client.chat.completions.create(
        model=model,
        messages=build_judge_messages(answer, hits),
        temperature=0,
    )
    return parse_verdict(response.choices[0].message.content or "")
