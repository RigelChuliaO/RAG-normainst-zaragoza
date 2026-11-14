"""Pruebas de chunk.py.

Dos grupos, como en test_extract.py:

1. PRUEBAS UNITARIAS: líneas fabricadas a mano que imitan la maquetación del
   BOE (sangría, negrita, letra pequeña). Comprueban cada regla del chunker por
   separado y no necesitan el PDF.

2. PRUEBAS SOBRE LOS DATOS REALES: ejecutan el chunker sobre el .lines.jsonl
   del RITE (en memoria, sin depender de un .chunks.jsonl que pudiera estar
   desfasado) y comprueban invariantes y lo que sabemos del documento. Si el
   .lines.jsonl no existe, se SALTAN.

Uso: python -m pytest -v
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pytest

from rag_normainst.ingest.chunk import (
    INDENT_X0,
    IT_RE,
    _heading_kind,
    build_chunks,
    build_units,
)

# =============================================================================
# 1. PRUEBAS UNITARIAS
# =============================================================================

SANGRIA = 107.7   # x0 de una línea que empieza párrafo
MARGEN = 90.7     # x0 de una línea que continúa el párrafo anterior


def _line(text: str, x0: float = SANGRIA, size: float = 10.0, bold: float = 0.0, page: int = 1) -> dict:
    """Fabrica una línea con los campos que produce extract.py."""
    return {"page": page, "pdf_page": page, "text": text, "bold_ratio": bold,
            "size": size, "font": "Arimo-Regular", "x0": x0, "y0": 0, "x1": 0, "y1": 0}


def _anexo() -> list[dict]:
    """Líneas que abren el Reglamento: a partir de aquí los ids son RITE:..."""
    return [_line("ANEXO", x0=280, bold=1.0),
            _line("Reglamento de Instalaciones Térmicas en los Edificios (RITE)", x0=150, bold=1.0)]


def _chunks(lines: list[dict], max_words: int = 300):
    return build_chunks(lines, "DOC", "v1", max_words)


def _palabras(n: int, palabra: str = "texto") -> str:
    return " ".join([palabra] * n)


def test_titulo_en_dos_lineas_se_une_y_no_pasa_al_cuerpo():
    """La línea pegada al margen tras un encabezado continúa su título."""
    lines = _anexo() + [
        _line("IT 1.2 EXIGENCIA DE EFICIENCIA ENERGÉTICA Y ENERGÍAS RENOVABLES Y"),
        _line("RESIDUALES.", x0=MARGEN),
        _line("Texto propio de la sección."),
    ]
    [c] = _chunks(lines)
    assert c.title == "Exigencia de eficiencia energética y energías renovables y residuales."
    assert c.text == "Texto propio de la sección."


def test_padre_sin_texto_no_es_chunk_pero_da_ruta_a_sus_hijos():
    lines = _anexo() + [
        _line("IT 1.1 EXIGENCIA DE BIENESTAR E HIGIENE"),
        _line("IT 1.1.1 Ámbito de aplicación"),
        _line("Esta sección se aplica a..."),
    ]
    chunks = _chunks(lines)
    assert [c.id for c in chunks] == ["RITE:IT-1.1.1"]
    assert "IT 1.1 Exigencia de bienestar e higiene" in chunks[0].path
    assert "IT 1.1 Exigencia de bienestar e higiene" in chunks[0].embed_text


def test_referencia_a_principio_de_linea_no_es_encabezado():
    """Una referencia que cae a principio de línea no está sangrada: es texto."""
    lines = _anexo() + [
        _line("IT 1.1.1 Ámbito de aplicación"),
        _line("Se cumplirá lo indicado en la"),
        _line("IT 1.2.4 Caracterización de la exigencia de eficiencia.", x0=MARGEN),
    ]
    [c] = _chunks(lines)
    assert c.id == "RITE:IT-1.1.1"
    assert "IT 1.2.4 Caracterización" in c.text
    assert c.refs == ["RITE:IT-1.2.4"]


def test_unidad_larga_se_parte_por_sus_apartados():
    lines = _anexo() + [
        _line("Artículo 5. Remisión a normas.", x0=MARGEN, bold=0.4),
        _line("1. " + _palabras(200)),
        _line("2. " + _palabras(200)),
    ]
    chunks = _chunks(lines, max_words=300)
    assert [c.id for c in chunks] == ["RITE:art-5#1", "RITE:art-5#2"]
    assert all(c.n_words <= 300 for c in chunks)
    assert chunks[1].text.startswith("2. ")
    assert all(c.pieces == 2 for c in chunks)
    assert chunks[0].embed_text.split("\n")[0] == chunks[1].embed_text.split("\n")[0]  # misma ruta


def test_unidades_cortas_distintas_no_se_fusionan():
    lines = _anexo() + [
        _line("Artículo 1. Objeto.", x0=MARGEN, bold=0.6),
        _line("Texto uno."),
        _line("Artículo 2. Ámbito.", x0=MARGEN, bold=0.4),
        _line("Texto dos."),
    ]
    chunks = _chunks(lines)
    assert [(c.id, c.text) for c in chunks] == [("RITE:art-1", "Texto uno."), ("RITE:art-2", "Texto dos.")]


def test_apendice_1_se_parte_en_una_definicion_por_chunk():
    lines = _anexo() + [
        _line("APÉNDICE 1", x0=268),
        _line("Términos y definiciones", x0=240, bold=1.0),
        _line("A efectos de este RITE, los términos se usarán así:"),
        _line("Aire de expulsión (EHA): (Exhaust air): es el aire extraído y"),
        _line("expulsado al exterior.", x0=MARGEN),
        _line("Aire exterior (ODA) (Outdoor air): aire que entra en el sistema."),
    ]
    chunks = _chunks(lines)
    assert [c.id for c in chunks] == [
        "RITE:AP1:introduccion", "RITE:AP1:aire-de-expulsion", "RITE:AP1:aire-exterior"]
    assert chunks[1].text == "Aire de expulsión (EHA): (Exhaust air): es el aire extraído y expulsado al exterior."


def test_tabla_queda_dentro_de_su_seccion():
    lines = _anexo() + [
        _line("IT 1.1.4.1.2 Temperatura operativa y humedad relativa"),
        _line("Los valores serán los de la tabla."),
        _line("Tabla 1.4.1.1 Condiciones interiores de diseño", size=8.0, bold=1.0),
        _line("Verano", size=8.0),
        _line("23...25", size=8.0),
    ]
    [c] = _chunks(lines)
    assert c.has_table
    assert "Tabla 1.4.1.1" in c.text and "23...25" in c.text


def test_ids_repetidos_paran_con_error():
    """Dos unidades con el mismo id romperían el golden set: debe fallar alto."""
    lines = _anexo() + [
        _line("Artículo 1. Objeto.", x0=MARGEN, bold=0.6), _line("Uno."),
        _line("Artículo 1. Objeto.", x0=MARGEN, bold=0.6), _line("Otra vez uno."),
    ]
    with pytest.raises(ValueError, match="repetidos"):
        _chunks(lines)


# =============================================================================
# 2. PRUEBAS SOBRE LOS DATOS REALES DEL RITE
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parents[1]
LINES_PATH = REPO_ROOT / "data" / "interim" / "BOE-A-2007-15820-consolidado.lines.jsonl"

# Cifras de referencia comprobadas el 14/11/2026 con MAX_WORDS = 250 (ADR-005).
# Si cambian a propósito (otro límite, otra versión del RITE), se actualizan aquí.
EXPECTED_CHUNKS = 417
EXPECTED_ARTICLES = 47
EXPECTED_DEFINITIONS = 106
MAX_WORDS = 250


@pytest.fixture(scope="module")
def real():
    """Ejecuta el chunker sobre las líneas reales; si no existen, salta."""
    if not LINES_PATH.exists():
        pytest.skip(f"No hay {LINES_PATH.name}: ejecuta antes extract.py sobre el PDF del RITE")
    with LINES_PATH.open(encoding="utf-8") as f:
        lines = [json.loads(raw) for raw in f]
    return lines, build_chunks(lines, "BOE-A-2007-15820", "02 de agosto de 2022", MAX_WORDS)


def test_cifras_de_referencia(real):
    _, chunks = real
    assert len(chunks) == EXPECTED_CHUNKS
    assert sum(c.id.startswith("RITE:AP1:") and c.id != "RITE:AP1:introduccion" for c in chunks) == EXPECTED_DEFINITIONS


def test_ningun_chunk_vacio_ni_por_encima_del_limite(real):
    _, chunks = real
    vacios = [c.id for c in chunks if not c.text.strip()]
    largos = [(c.id, c.n_words) for c in chunks if c.n_words > MAX_WORDS]
    assert not vacios, f"chunks vacíos: {vacios[:5]}"
    assert not largos, f"chunks por encima de {MAX_WORDS} palabras: {largos[:5]}"


def test_ids_unicos_y_deterministas(real):
    lines, chunks = real
    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids))
    otra_vez = build_chunks(lines, "BOE-A-2007-15820", "02 de agosto de 2022", MAX_WORDS)
    assert [(c.id, c.embed_text) for c in otra_vez] == [(c.id, c.embed_text) for c in chunks]


def test_se_conserva_todo_el_texto_de_cuerpo(real):
    """Lo que entra en las unidades sale en los chunks, y lo que queda fuera
    son solo encabezados, títulos y la firma del Real Decreto."""
    lines, chunks = real
    units = build_units(lines)
    palabras_unidades = sum(len(l["text"].split()) for u in units for l in u.lines)
    assert palabras_unidades == sum(c.n_words for c in chunks)

    dentro = {id(l) for u in units for l in u.lines}
    fuera_sospechosas = [
        l["text"] for l in lines
        if id(l) not in dentro
        and not _heading_kind(l)            # encabezado
        and l["bold_ratio"] < 0.9           # título en negrita (Parte, Capítulo...)
        and l["size"] >= 10                 # firma en letra pequeña
        and l["x0"] >= INDENT_X0            # continuación de título (pegada al margen)
    ]
    assert not fuera_sospechosas, f"texto de cuerpo perdido: {fuera_sospechosas[:5]}"


def test_estan_todos_los_articulos_del_reglamento(real):
    _, chunks = real
    nums = {int(m.group(1)) for c in chunks if (m := re.match(r"RITE:art-(\d+)", c.id))}
    assert nums == set(range(1, EXPECTED_ARTICLES + 1))


def test_todas_las_secciones_it_hoja_tienen_chunk(real):
    lines, chunks = real
    nums = [re.sub(r"\s", "", m.group(1)).rstrip(".")
            for l in lines if l["x0"] >= INDENT_X0 and (m := IT_RE.match(l["text"]))]
    hojas = {n for n in nums if not any(o.startswith(n + ".") for o in nums)}
    con_chunk = {m.group(1) for c in chunks if (m := re.match(r"RITE:IT-([\d.]+)", c.id))}
    assert not hojas - con_chunk, f"IT hoja sin chunk: {sorted(hojas - con_chunk)[:10]}"


def test_ningun_chunk_contiene_dos_encabezados(real):
    """Si un chunk llevara dentro otro encabezado, se habrían fusionado dos unidades."""
    _, chunks = real
    patron = re.compile(r"\n(Artículo \d+\. [A-ZÁÉÍÓÚ]|IT \d+(\.\d+)+ [A-ZÁÉÍÓÚ])")
    fusionados = [c.id for c in chunks if patron.search(c.text)]
    assert not fusionados, f"chunks con dos encabezados: {fusionados[:5]}"


def test_trozos_numerados_sin_huecos(real):
    """Una unidad partida en n trozos tiene exactamente #1..#n, en orden."""
    _, chunks = real
    por_unidad: dict[str, list] = {}
    for c in chunks:
        por_unidad.setdefault(c.id.split("#")[0], []).append(c)
    for base, trozos in por_unidad.items():
        n = trozos[0].pieces
        esperado = [base] if n == 1 else [f"{base}#{k}" for k in range(1, n + 1)]
        assert [c.id for c in trozos] == esperado, f"trozos mal numerados en {base}"
