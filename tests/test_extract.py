"""Pruebas de extract.py.

Hay dos grupos, con propósitos distintos:

1. PRUEBAS UNITARIAS (no necesitan el PDF real).
   Comprueban la lógica del extractor con datos fabricados: un PDF pequeño
   generado al vuelo y spans escritos a mano. Se ejecutan en cualquier máquina,
   también en un clon limpio del repositorio o en CI (fase 3), donde el PDF
   del BOE no existe porque no se sube a git.

2. PRUEBAS SOBRE LOS DATOS REALES (necesitan haber ejecutado extract.py).
   Comprueban el .lines.jsonl del RITE contra invariantes y contra lo que
   sabemos del dominio (artículos 1..N sin huecos, IT con su padre...).
   Son las pruebas de no regresión del corpus: si un cambio en el código hace
   desaparecer un artículo, aquí falla. Si el .lines.jsonl no existe, se
   SALTAN (skip) en vez de fallar.

Uso, desde la raíz del repo y con el entorno activado:
  python -m pytest            # todas
  python -m pytest -v         # con el nombre de cada prueba
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pymupdf
import pytest

from rag_normainst.ingest.extract import (
    DISCLAIMER_RE,
    FOOTER_RE,
    HEADER_TEXTS,
    _line_from_spans,
    extract,
)

# =============================================================================
# 1. PRUEBAS UNITARIAS
# =============================================================================


def _span(text: str, bold: bool = False, size: float = 10.0) -> dict:
    """Fabrica un span con los campos que usa _line_from_spans."""
    return {
        "text": text,
        "flags": 16 if bold else 0,
        "font": "Arimo-Bold" if bold else "Arimo-Regular",
        "size": size,
    }


def test_bold_ratio_parcial_como_en_un_articulo():
    """Número en negrita + título sin negrita da una proporción intermedia."""
    spans = [_span("Artículo 2. ", bold=True), _span("Ámbito de aplicación.")]
    line = _line_from_spans(spans, (0, 0, 100, 10), pdf_page=1)
    assert line.text == "Artículo 2. Ámbito de aplicación."
    # 11 caracteres en negrita ("Artículo 2.") de 32 en total.
    assert line.bold_ratio == pytest.approx(11 / 32, abs=0.01)
    assert line.font == "Arimo-Regular"  # la fuente con más caracteres


def test_linea_vacia_devuelve_none():
    assert _line_from_spans([_span("   "), _span(" ")], (0, 0, 1, 1), pdf_page=1) is None


def test_espacios_normalizados():
    line = _line_from_spans([_span("IT  1.1  Ámbito\tde aplicación ")], (0, 0, 1, 1), pdf_page=1)
    assert line.text == "IT 1.1 Ámbito de aplicación"


def _fake_boe_pdf(path: Path, with_body_marker: bool = True) -> Path:
    """Crea un PDF pequeño con la anatomía de un consolidado del BOE.

    Página 1: portada + índice. Páginas 2-3: cuerpo. La página 3 lleva el
    aviso legal. Todas llevan cabecera arriba y "Página N" abajo.
    """
    doc = pymupdf.open()
    pages = [
        ["Referencia: BOE-A-2007-15820", "ÍNDICE", "Artículo 1. Objeto."],
        (["TEXTO CONSOLIDADO", "Última modificación: 02 de agosto de 2022"] if with_body_marker else [])
        + ["Artículo 1. Objeto.", "Texto del artículo uno."],
        ["Este documento es de carácter informativo y no tiene valor jurídico.", "Texto final."],
    ]
    for n, lines in enumerate(pages, start=1):
        page = doc.new_page()  # A4 por defecto: 595 x 842 puntos
        page.insert_text((150, 40), "BOLETÍN OFICIAL DEL ESTADO", fontsize=14)
        page.insert_text((180, 60), "LEGISLACIÓN CONSOLIDADA", fontsize=10)
        y = 150
        for text in lines:
            page.insert_text((60, y), text, fontsize=10)
            y += 16
        page.insert_text((270, 800), f"Página {n}", fontsize=9)
    doc.save(path)
    return path


def test_extract_limpia_cabecera_pie_preliminares_y_aviso(tmp_path):
    body, meta = extract(_fake_boe_pdf(tmp_path / "falso.pdf"))
    texts = [line.text for line in body]

    assert texts == ["Artículo 1. Objeto.", "Texto del artículo uno.", "Texto final."]
    assert meta["doc_id"] == "BOE-A-2007-15820"
    assert meta["version"] == "02 de agosto de 2022"
    assert meta["dropped"]["header"] == 6       # 2 por página x 3 páginas
    assert meta["dropped"]["footer"] == 3
    assert meta["dropped"]["disclaimer"] == 1
    # El número de página sale del pie impreso.
    assert [line.page for line in body] == [2, 2, 3]


def test_extract_falla_si_no_encuentra_el_inicio_del_cuerpo(tmp_path):
    """Sin "TEXTO CONSOLIDADO" debe parar, no indexar el índice en silencio."""
    pdf = _fake_boe_pdf(tmp_path / "sin_marca.pdf", with_body_marker=False)
    with pytest.raises(ValueError, match="TEXTO CONSOLIDADO"):
        extract(pdf)


# =============================================================================
# 2. PRUEBAS SOBRE LOS DATOS REALES DEL RITE
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parents[1]
INTERIM = REPO_ROOT / "data" / "interim"
STEM = "BOE-A-2007-15820-consolidado"

# Lo que sabemos de ESTE documento (comprobado a mano el 13/11/2026).
# Si se cambia de versión del RITE, estos valores hay que revisarlos a propósito.
EXPECTED_DOC_ID = "BOE-A-2007-15820"
EXPECTED_VERSION = "02 de agosto de 2022"
BODY_FIRST_PAGE = 5    # el cuerpo empieza tras portada e índice
BODY_LAST_PAGE = 96    # la 97 solo tenía el aviso legal, que se descarta

ARTICLE_RE = re.compile(r"^Artículo (\d+)\. ")
# Tolera espacios dentro del número: el PDF trae la errata "IT 1.2. 4.7".
IT_RE = re.compile(r"^IT (\d+(?:\.\s?\d+)*)\.? [A-ZÁÉÍÓÚÑ]")


@pytest.fixture(scope="module")
def real():
    """Carga el .lines.jsonl y el .meta.json reales; si no existen, salta."""
    lines_path = INTERIM / f"{STEM}.lines.jsonl"
    meta_path = INTERIM / f"{STEM}.meta.json"
    if not lines_path.exists() or not meta_path.exists():
        pytest.skip(f"No hay {lines_path.name}: ejecuta antes extract.py sobre el PDF del RITE")
    with lines_path.open(encoding="utf-8") as f:
        lines = [json.loads(raw) for raw in f]
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return lines, meta


def test_metadatos_del_documento(real):
    lines, meta = real
    assert meta["doc_id"] == EXPECTED_DOC_ID
    assert meta["version"] == EXPECTED_VERSION
    assert meta["n_lines"] == len(lines)


def test_todas_las_lineas_tienen_pagina(real):
    lines, _ = real
    sin_pagina = [l["text"] for l in lines if l["page"] is None]
    assert not sin_pagina, f"{len(sin_pagina)} líneas sin página, p. ej.: {sin_pagina[:3]}"


def test_paginas_en_orden_y_sin_huecos(real):
    lines, _ = real
    pages = [l["page"] for l in lines]
    assert pages == sorted(pages), "las páginas no van en orden de lectura"
    assert min(pages) == BODY_FIRST_PAGE
    assert max(pages) == BODY_LAST_PAGE
    faltan = sorted(set(range(BODY_FIRST_PAGE, BODY_LAST_PAGE + 1)) - set(pages))
    assert not faltan, f"páginas del cuerpo sin ninguna línea: {faltan}"


def test_sin_restos_de_cabecera_pie_ni_aviso(real):
    lines, _ = real
    restos = [
        l["text"] for l in lines
        if l["text"] in HEADER_TEXTS or FOOTER_RE.match(l["text"]) or DISCLAIMER_RE.match(l["text"])
    ]
    assert not restos, f"quedan líneas de maquetación del BOE: {restos[:5]}"


def test_sin_lineas_vacias_ni_caracteres_rotos(real):
    lines, _ = real
    assert all(l["text"] for l in lines), "hay líneas vacías"
    rotas = [l["text"] for l in lines if "�" in l["text"]]
    assert not rotas, f"caracteres de sustitución (�) en: {rotas[:3]}"


def test_articulos_consecutivos_sin_huecos_ni_repetidos(real):
    """Si un cambio hace desaparecer un artículo, esta prueba lo detecta."""
    lines, _ = real
    nums = [int(m.group(1)) for l in lines if (m := ARTICLE_RE.match(l["text"]))]
    assert nums, "no se ha encontrado ningún encabezado de artículo"
    repetidos = [n for n, c in Counter(nums).items() if c > 1]
    huecos = sorted(set(range(1, max(nums) + 1)) - set(nums))
    assert not repetidos, f"artículos repetidos: {repetidos}"
    assert not huecos, f"faltan artículos: {huecos}"


def test_cada_instruccion_tecnica_tiene_su_padre(real):
    """Si existe IT 1.1.4.1.2 tiene que existir IT 1.1.4.1, y así hacia arriba.

    Los de segundo nivel (IT 1.1) no se comprueban: su padre (IT 1) aparece
    como "INSTRUCCIÓN TÉCNICA IT 1. ..." y no empieza por "IT".
    """
    lines, _ = real
    nums = [
        re.sub(r"\s", "", m.group(1)).rstrip(".")
        for l in lines if (m := IT_RE.match(l["text"]))
    ]
    assert nums, "no se ha encontrado ningún encabezado IT"
    vistos = set(nums)
    repetidos = [n for n, c in Counter(nums).items() if c > 1]
    huerfanos = [n for n in nums if n.count(".") >= 2 and n.rsplit(".", 1)[0] not in vistos]
    assert not repetidos, f"IT repetidas: {repetidos}"
    assert not huerfanos, f"IT sin su sección padre: {huerfanos}"
