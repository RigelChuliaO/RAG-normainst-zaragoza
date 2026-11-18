"""Generación: pregunta + chunks recuperados -> respuesta del LLM con citas.

Principio clave: la cita la construye el CÓDIGO, no el LLM. Al modelo se le pasan
los chunks numerados [1], [2]... y se le pide que cite con esos números. Después
se traducen a "RITE, IT 1.1.4.1.2, pág. 29" desde los metadatos. Así el modelo
no puede inventar un artículo: solo elegir entre los que le hemos dado, y una
marca que no corresponde a ningún chunk se detecta automáticamente.

El LLM se llama con el cliente `openai` contra el endpoint compatible de Ollama
(http://localhost:11434/v1). El mismo código sirve contra Azure OpenAI cambiando
la URL base y la clave.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

DEFAULT_LLM = "qwen3:4b-instruct"
OLLAMA_BASE_URL = "http://localhost:11434/v1"
# Ventana de contexto que Ollama da al modelo por defecto (se ve en `ollama ps`).
# Si el prompt llega a llenarla, Ollama recorta el principio SIN avisar.
NUM_CTX = 4096
NO_CONSTA = "No consta en el RITE."

SYSTEM_PROMPT = f"""Eres un asistente técnico que responde preguntas sobre el Reglamento de Instalaciones Térmicas en los Edificios (RITE).

Reglas obligatorias:
1. Responde ÚNICAMENTE con la información de los FRAGMENTOS que se te dan. No uses conocimientos propios.
2. Cita cada afirmación con el número de su fragmento entre corchetes, por ejemplo [2]. Puedes citar varios: [1][3].
3. Si los fragmentos no contienen la respuesta, responde exactamente: "{NO_CONSTA}" y nada más.
4. Responde en español, de forma concisa pero completa: incluye las condiciones, excepciones y limitaciones que aparezcan en los fragmentos, aunque estén en fragmentos distintos.
5. Copia los valores numéricos y sus unidades tal como aparecen.
6. No repitas las cabeceras de los fragmentos; la lista de fuentes se añade aparte."""

CITE_RE = re.compile(r"\[(\d+)\]")


def is_no_consta(text: str) -> bool:
    """¿La respuesta es SOLO «No consta en el RITE.»? (sin comillas, puntos ni espacios de más)."""
    return text.strip().strip('"«»*. ').lower() == NO_CONSTA.rstrip(".").lower()


def mentions_no_consta(text: str) -> bool:
    """¿Aparece la frase en algún sitio? Si además hay respuesta, es una respuesta MIXTA."""
    return NO_CONSTA.rstrip(".").lower() in text.lower()


@dataclass
class Citation:
    label: int
    id: str
    unit: str
    title: str
    page: int

    def __str__(self) -> str:
        return f"[{self.label}] RITE, {self.unit}. {self.title} (pág. {self.page})"


@dataclass
class Answer:
    question: str
    text: str
    citations: list[Citation] = field(default_factory=list)  # solo las que el modelo usó
    retrieved_ids: list[str] = field(default_factory=list)    # lo que se le pasó
    invalid_labels: list[int] = field(default_factory=list)   # marcas sin chunk: alarma
    no_consta: bool = False          # la respuesta es SOLO «No consta en el RITE.»
    mixed_no_consta: bool = False    # responde Y añade «No consta» (p. ej. al final)
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    seconds_retrieve: float = 0.0
    seconds_generate: float = 0.0


def format_context(hits) -> str:
    """Los chunks numerados, cada uno con su cabecera (unidad, título, página)."""
    blocks = []
    for n, h in enumerate(hits, start=1):
        blocks.append(f"[{n}] {h.unit}. {h.title} (pág. {h.page_start})\n{h.text}")
    return "\n\n".join(blocks)


def build_messages(question: str, hits) -> list[dict]:
    """Mensajes del chat: instrucciones (system) y fragmentos + pregunta (user)."""
    user = f"FRAGMENTOS\n\n{format_context(hits)}\n\nPREGUNTA\n{question}"
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def strip_thinking(text: str) -> str:
    """Quita un razonamiento <think>…</think> si el modelo lo emitiera."""
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    return text.strip()


def parse_citations(text: str, hits) -> tuple[list[Citation], list[int]]:
    """Traduce las marcas [n] a citas reales; devuelve también las marcas inválidas."""
    labels = sorted({int(n) for n in CITE_RE.findall(text)})
    valid = [n for n in labels if 1 <= n <= len(hits)]
    invalid = [n for n in labels if not 1 <= n <= len(hits)]
    citations = [
        Citation(n, hits[n - 1].id, hits[n - 1].unit, hits[n - 1].title, hits[n - 1].page_start)
        for n in valid
    ]
    return citations, invalid


def generate(question: str, hits, client, model: str = DEFAULT_LLM) -> Answer:
    """Llama al LLM con los chunks y construye la respuesta con sus citas."""
    t0 = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=build_messages(question, hits),
        temperature=0,  # misma pregunta -> misma respuesta: imprescindible para evaluar
    )
    seconds = time.perf_counter() - t0
    text = strip_thinking(response.choices[0].message.content or "")
    citations, invalid = parse_citations(text, hits)
    usage = getattr(response, "usage", None)
    prompt_tokens = getattr(usage, "prompt_tokens", None)
    if prompt_tokens is not None and prompt_tokens >= NUM_CTX - 64:
        # El prompt ha llenado la ventana: Ollama habrá recortado el principio.
        raise RuntimeError(
            f"el prompt ocupa {prompt_tokens} tokens y la ventana es de {NUM_CTX}: "
            "se ha truncado. Usa menos chunks (k) o amplía la ventana."
        )
    return Answer(
        question=question,
        text=text,
        citations=citations,
        retrieved_ids=[h.id for h in hits],
        invalid_labels=invalid,
        no_consta=is_no_consta(text),
        mixed_no_consta=mentions_no_consta(text) and not is_no_consta(text),
        prompt_tokens=prompt_tokens,
        completion_tokens=getattr(usage, "completion_tokens", None),
        seconds_generate=seconds,
    )


def make_client(base_url: str = OLLAMA_BASE_URL):
    """Cliente OpenAI apuntando a Ollama (la clave es obligatoria pero no se usa)."""
    from openai import OpenAI
    return OpenAI(base_url=base_url, api_key="ollama")
