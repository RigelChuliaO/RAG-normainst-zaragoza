"""Etapa 1 de la ingesta: PDF consolidado del BOE -> líneas de texto limpias con su formato.

Este módulo solo EXTRAE y LIMPIA. No decide qué es un encabezado ni dónde
empieza un chunk: eso es trabajo de chunk.py. Aquí se conservan las señales
de maquetación (negrita, tamaño de letra, posición) que chunk.py necesitará
para tomar esa decisión.

Qué se elimina (y se cuenta, para que se pueda revisar):
  - preliminares: portada e índice, es decir, todo lo anterior a la línea
    "TEXTO CONSOLIDADO" que abre el cuerpo
  - cabecera de página: "BOLETÍN OFICIAL DEL ESTADO / LEGISLACIÓN CONSOLIDADA"
  - pie de página: "Página N" (su número se guarda como página impresa)
  - aviso legal del final del documento: "Este documento es de carácter
    informativo y no tiene valor jurídico."
  - bloques de imagen (el logo del BOE)

Salida (en --out-dir):
  <nombre>.lines.jsonl  un objeto JSON por línea de texto, en orden de lectura
  <nombre>.meta.json    id del documento, versión del corpus, hash del fichero,
                        recuento de lo descartado

Uso (desde la raíz del repo, con el entorno activado):
  python -m rag_normainst.ingest.extract "data/raw/BOE-A-2007-15820-consolidado RITE.pdf"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import pymupdf

# --- Patrones propios de este documento (comprobados a ojo en el PDF del RITE) ---

HEADER_TEXTS = {"BOLETÍN OFICIAL DEL ESTADO", "LEGISLACIÓN CONSOLIDADA"}
FOOTER_RE = re.compile(r"^Página\s+(\d+)$")
BODY_START_RE = re.compile(r"^TEXTO CONSOLIDADO$")
VERSION_RE = re.compile(r"Última modificación:\s*(.+)$")
DOC_ID_RE = re.compile(r"Referencia:\s*(BOE-[A-Z]-\d{4}-\d+)")
# Aviso legal que el BOE añade en la última página. Se filtra por la frase
# COMPLETA (^...$) y no por posición: está arriba de la página (y0≈94), fuera
# de las zonas de cabecera y pie. Exigir la línea entera evita borrar un
# párrafo de la norma que contuviera una expresión parecida.
DISCLAIMER_RE = re.compile(
    r"^Este documento es de carácter informativo y no tiene valor jurídico\.$"
)

# Zonas de cabecera y pie como fracción de la altura de página. Son ESTIMACIONES:
# compruébalas con el resumen que se imprime al final (líneas descartadas por motivo).
TOP_ZONE = 0.12
BOTTOM_ZONE = 0.90

# En span["flags"] de PyMuPDF, el bit 4 (valor 16) indica negrita.
BOLD_FLAG = 16


@dataclass
class Line:
    page: int | None  # número de página impreso, sacado del pie "Página N"
    pdf_page: int     # página física dentro del fichero, empezando en 1
    text: str
    bold_ratio: float  # proporción de caracteres en negrita (de 0.0 a 1.0)
    size: float        # tamaño de letra mayor de la línea
    font: str          # fuente que cubre más caracteres
    x0: float
    y0: float
    x1: float
    y1: float


def _clean(text: str) -> str:
    """Normaliza los espacios: espacios duros, tabuladores, espacios repetidos."""
    return re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()


def _is_bold(span: dict) -> bool:
    # Algunos PDF no activan el bit pero usan una fuente con "Bold" en el nombre;
    # se aceptan las dos señales.
    return bool(span["flags"] & BOLD_FLAG) or "bold" in span["font"].lower()


def _line_from_spans(spans: list[dict], bbox, pdf_page: int) -> Line | None:
    """Une los spans de una línea visual. Devuelve None si la línea está vacía.

    Una misma línea visual puede llegar partida en varios spans cuando el
    formato cambia a mitad de línea (p. ej. un número en negrita seguido de
    un título en redonda).
    """
    text = _clean("".join(s["text"] for s in spans))
    if not text:
        return None

    chars_bold = sum(len(s["text"].strip()) for s in spans if _is_bold(s))
    chars_total = sum(len(s["text"].strip()) for s in spans) or 1

    font_chars: Counter[str] = Counter()
    for s in spans:
        font_chars[s["font"]] += len(s["text"].strip())

    x0, y0, x1, y1 = bbox
    return Line(
        page=None,
        pdf_page=pdf_page,
        text=text,
        bold_ratio=round(chars_bold / chars_total, 2),
        size=round(max(s["size"] for s in spans), 1),
        font=font_chars.most_common(1)[0][0],
        x0=round(x0, 1), y0=round(y0, 1), x1=round(x1, 1), y1=round(y1, 1),
    )


def extract_page_lines(page: pymupdf.Page, drops: Counter) -> list[Line]:
    """Devuelve las líneas de cuerpo de una página, sin cabecera ni pie.

    El número de página impreso que aparece en el pie se escribe en todas
    las líneas de la página.
    """
    height = page.rect.height
    data = page.get_text("dict", sort=True)

    lines: list[Line] = []
    printed_page: int | None = None

    for block in data["blocks"]:
        if block["type"] != 0:  # 1 = bloque de imagen, no tiene "lines"
            drops["image_block"] += 1
            continue
        for raw in block["lines"]:
            line = _line_from_spans(raw["spans"], raw["bbox"], page.number + 1)
            if line is None:
                continue

            if line.text in HEADER_TEXTS and line.y1 < height * TOP_ZONE:
                drops["header"] += 1
                continue

            m = FOOTER_RE.match(line.text)
            if m and line.y0 > height * BOTTOM_ZONE:
                printed_page = int(m.group(1))
                drops["footer"] += 1
                continue

            if DISCLAIMER_RE.match(line.text):
                drops["disclaimer"] += 1
                continue

            lines.append(line)

    if printed_page is None:
        drops["pages_without_footer"] += 1
    for line in lines:
        line.page = printed_page
    return lines


def split_front_matter(lines: list[Line], drops: Counter) -> tuple[list[Line], dict]:
    """Descarta portada e índice; captura el id del documento y la versión.

    El cuerpo empieza en la línea "TEXTO CONSOLIDADO". Si no se encuentra,
    se para con un error en vez de adivinar: indexar el índice sin darse
    cuenta crearía chunks que son solo un título y ensucian la recuperación.
    """
    meta = {"doc_id": None, "version": None}

    start = None
    for i, line in enumerate(lines):
        if meta["doc_id"] is None and (m := DOC_ID_RE.search(line.text)):
            meta["doc_id"] = m.group(1)
        if BODY_START_RE.match(line.text):
            start = i
            break

    if start is None:
        raise ValueError(
            "No se encuentra 'TEXTO CONSOLIDADO': no se puede localizar el inicio del cuerpo"
        )

    body = lines[start + 1:]
    drops["front_matter"] += start + 1

    # La línea de versión va justo después de "TEXTO CONSOLIDADO".
    if body and (m := VERSION_RE.search(body[0].text)):
        meta["version"] = m.group(1).strip()
        body = body[1:]
        drops["version_line"] += 1

    return body, meta


def file_sha256(path: Path) -> str:
    """Hash del PDF de origen: dice si el corpus ha cambiado entre ejecuciones."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def extract(pdf_path: Path) -> tuple[list[Line], dict]:
    """Extracción completa: todas las páginas -> líneas de cuerpo limpias + metadatos."""
    drops: Counter = Counter()
    all_lines: list[Line] = []

    with pymupdf.open(pdf_path) as doc:
        n_pages = doc.page_count
        for page in doc:
            all_lines.extend(extract_page_lines(page, drops))

    body, meta = split_front_matter(all_lines, drops)

    meta.update({
        "source_file": pdf_path.name,
        "sha256": file_sha256(pdf_path),
        "n_pages": n_pages,
        "n_lines": len(body),
        "dropped": dict(drops),
        "pymupdf_version": pymupdf.__version__,
    })
    return body, meta


def write_outputs(lines: list[Line], meta: dict, out_dir: Path, stem: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    # encoding="utf-8" va explícito a propósito: en Windows el valor por defecto
    # es cp1252, que rompe o deforma tildes y símbolos como "º" o "≤".
    with (out_dir / f"{stem}.lines.jsonl").open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(asdict(line), ensure_ascii=False) + "\n")
    with (out_dir / f"{stem}.meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def print_summary(lines: list[Line], meta: dict) -> None:
    """Lo que hay que mirar antes de fiarse de la salida."""
    print(f"doc_id:   {meta['doc_id']}")
    print(f"versión:  {meta['version']}")
    print(f"páginas:  {meta['n_pages']}   líneas de cuerpo: {meta['n_lines']}")
    print(f"descartado: {meta['dropped']}")

    sizes = Counter(line.size for line in lines)
    print("tamaños de letra (tamaño: líneas):", dict(sorted(sizes.items())))
    print("líneas en negrita:", sum(1 for line in lines if line.bold_ratio >= 0.9))

    if any(line.text == "ÍNDICE" for line in lines):
        print("AVISO: aparece 'ÍNDICE' dentro del cuerpo: el corte de los preliminares está mal")

    print("primeras líneas del cuerpo:")
    for line in lines[:5]:
        print(f"  p{line.page} | {line.text[:80]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pdf", type=Path, help="ruta al PDF consolidado del BOE")
    parser.add_argument("--out-dir", type=Path, default=Path("data/interim"))
    args = parser.parse_args()

    lines, meta = extract(args.pdf)
    write_outputs(lines, meta, args.out_dir, args.pdf.stem)
    print_summary(lines, meta)


if __name__ == "__main__":
    main()
