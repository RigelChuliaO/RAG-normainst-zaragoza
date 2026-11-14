"""Etapa 2 de la ingesta: líneas limpias -> chunks por estructura (structure-aware).

Lee el .lines.jsonl de extract.py y produce un chunk por unidad citable del RITE:
  - artículo o disposición (del Real Decreto o del Reglamento)
  - subsección IT con texto propio (en la práctica, la de nivel más profundo)
  - definición del Apéndice 1; el resto de apéndices, uno por apéndice
  - preámbulo del Real Decreto

Reglas (ADR-005):
  - Los encabezados sin texto propio (PARTE, CAPÍTULO, IT padres) no son chunks:
    solo aportan su título a la ruta de sus hijos.
  - Las unidades largas se parten por sus apartados numerados ("1.", "2."...) y,
    si no basta, por párrafos, hasta MAX_WORDS palabras. Cada trozo lleva un id
    propio (…#1, …#2) y la misma ruta.
  - Nunca se juntan dos unidades distintas: un artículo corto se queda corto.
  - Las tablas van dentro del chunk de su sección (has_table = True).
  - Cada chunk guarda dos textos: `text` (cuerpo limpio, para el prompt) y
    `embed_text` (ruta de títulos + cuerpo, para el embedding).
  - Los ids son deterministas y legibles: RITE:art-2, RITE:IT-1.1.4.1.2...

Señales de maquetación que se usan (comprobadas en el PDF real):
  - Un párrafo nuevo empieza con sangría (x0 ≈ 107.7); una línea que continúa
    el párrafo anterior va pegada al margen (x0 ≈ 90.7).
  - Los encabezados IT empiezan párrafo (sangrados); una referencia cruzada que
    cae a principio de línea no lo está.
  - Los títulos largos siguen en la línea siguiente, pegada al margen.
  - Las tablas van en letra de menos de 10 pt.

Uso (desde la raíz del repo, con el entorno activado):
  python -m rag_normainst.ingest.chunk "data/interim/BOE-A-2007-15820-consolidado.lines.jsonl"
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Límite de palabras de cuerpo por chunk: es una aproximación barata del límite real,
# la ventana del modelo de embeddings (512 tokens en e5-base). Con 300 palabras, 7
# chunks pasaban de 512 tokens (texto con códigos UNE ≈1,9 tokens/palabra; rutas de
# hasta 96 tokens). Con 250 caben. La garantía no es este número: al indexar se
# comprueba cada chunk con el tokenizer real y se para si alguno no cabe (ADR-005).
MAX_WORDS = 250

# x0 a partir del cual una línea de cuerpo empieza párrafo (sangría).
INDENT_X0 = 100.0
BODY_SIZE = 10.0

# --- Patrones de encabezado (se aplican a líneas de 10 pt) -------------------
ANEXO_RE = re.compile(r"^ANEXO$")
PARTE_RE = re.compile(r"^PARTE (I{1,3})\.?$")
CAPITULO_RE = re.compile(r"^CAPÍTULO ([IVXL]+)$")
APENDICES_RE = re.compile(r"^APÉNDICES$")
APENDICE_RE = re.compile(r"^APÉNDICE (\d+)$")
IT_ROOT_RE = re.compile(r"^INSTRUCCIÓN TÉCNICA IT (\d+)\.?\s+(.*)$")
# Tolera el espacio de la errata del PDF: "IT 1.2. 4.7".
IT_RE = re.compile(r"^IT (\d+(?:\.\s?\d+)+)\.?\s+([A-ZÁÉÍÓÚÑ].*)$")
ARTICULO_RE = re.compile(r"^Artículo (\d+|único)\.\s+(.*)$")
DISPOSICION_RE = re.compile(
    r"^Disposición (adicional|transitoria|derogatoria|final) (\w+)\.\s+(.*)$"
)
# Definición del Apéndice 1: "Término (sigla) (English): definición".
DEFINICION_RE = re.compile(r"^([A-ZÁÉÍÓÚÑ][^:]{1,120}?):\s")
APARTADO_RE = re.compile(r"^\d+\.\s")
# Título de tabla: algunas tablas del RITE van en letra de 10 pt y no se detectan por tamaño.
TABLA_RE = re.compile(r"(?:^|\n)Tabla \d")

# --- Referencias cruzadas -----------------------------------------------------
REF_ARTICULO_RE = re.compile(r"\bart[íi]culos? (\d+)(?![\d.])(?!\s+del?\s+(?:Real|Ley|Reglamento|Decreto))")
REF_IT_RE = re.compile(r"\b(?:IT|[Ii]nstrucción [Tt]écnica)\s+(\d+(?:\.\d+)+)")


@dataclass
class Unit:
    """Una unidad del documento: un encabezado y el cuerpo que le sigue."""
    uid: str                 # id base, p. ej. "RITE:art-2"
    part: str                # "RD" o "RITE"
    label: str               # cómo se cita: "Artículo 2", "IT 1.1.4.1.2"...
    title: str               # título del encabezado
    path: list[str]          # títulos de los ancestros, de fuera hacia dentro
    page: int | None         # página del encabezado
    lines: list[dict] = field(default_factory=list)


@dataclass
class Chunk:
    id: str
    doc: str
    version: str | None
    part: str
    unit: str
    title: str
    path: list[str]
    piece: int               # número de trozo dentro de la unidad (1 si no se parte)
    pieces: int              # total de trozos de la unidad
    page_start: int | None
    page_end: int | None
    has_table: bool
    refs: list[str]
    n_words: int
    text: str
    embed_text: str


# =============================================================================
# 1. De líneas a unidades
# =============================================================================


def _is_body(line: dict) -> bool:
    return line["size"] >= BODY_SIZE


def _starts_paragraph(line: dict) -> bool:
    return line["x0"] >= INDENT_X0


def _slug(text: str) -> str:
    """'Aire de expulsión' -> 'aire-de-expulsion'."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def _title_case_first(text: str) -> str:
    """'EXIGENCIA DE BIENESTAR E HIGIENE' -> 'Exigencia de bienestar e higiene'."""
    if text.isupper():
        return text[:1] + text[1:].lower()
    return text


def _absorb_title(lines: list[dict], i: int, title: str) -> tuple[str, int]:
    """Une al título las líneas siguientes que lo continúan (pegadas al margen).

    Devuelve el título completo y el índice de la primera línea que NO es título.
    """
    j = i + 1
    while (
        j < len(lines)
        and _is_body(lines[j])
        and not _starts_paragraph(lines[j])
        and lines[j]["x0"] < INDENT_X0
        and not _heading_kind(lines[j])
    ):
        title = f"{title} {lines[j]['text']}"
        j += 1
    return title.strip(), j


def _heading_kind(line: dict) -> str | None:
    """Tipo de encabezado de una línea, o None si es texto normal."""
    if not _is_body(line):
        return None
    t = line["text"]
    if ANEXO_RE.match(t) and line["bold_ratio"] >= 0.9:
        return "anexo"
    if PARTE_RE.match(t):
        return "parte"
    if CAPITULO_RE.match(t):
        return "capitulo"
    if APENDICES_RE.match(t):
        return "apendices"
    if APENDICE_RE.match(t):
        return "apendice"
    if IT_ROOT_RE.match(t):
        return "it_root"
    if IT_RE.match(t) and _starts_paragraph(line):
        return "it"
    # Artículos y disposiciones: número en negrita, título en cursiva.
    if ARTICULO_RE.match(t) and line["bold_ratio"] > 0:
        return "articulo"
    if DISPOSICION_RE.match(t) and line["bold_ratio"] > 0:
        return "disposicion"
    return None


def build_units(lines: list[dict]) -> list[Unit]:
    """Recorre las líneas y las reparte en unidades, con la ruta de cada una."""
    units: list[Unit] = []
    part = "RD"
    rd_path = ["Real Decreto 1027/2007"]
    parte_title: str | None = None      # "Parte I. Disposiciones generales"
    capitulo_title: str | None = None   # "Capítulo II. Exigencias técnicas"
    it_titles: dict[str, str] = {}      # "1.1.4" -> "IT 1.1.4 Caracterización..."

    current = Unit("RD:preambulo", "RD", "Preámbulo", "Preámbulo", rd_path,
                   lines[0]["page"] if lines else None)
    units.append(current)

    def start(unit: Unit) -> None:
        nonlocal current
        current = unit
        units.append(unit)

    i = 0
    while i < len(lines):
        line = lines[i]
        kind = _heading_kind(line)
        t = line["text"]

        if kind is None:
            # Firma del Real Decreto (letra pequeña antes del anexo): fuera.
            if part == "RD" and not _is_body(line):
                i += 1
                continue
            current.lines.append(line)
            i += 1
            continue

        if kind == "anexo":
            part = "RITE"
            # La línea siguiente es el título del Reglamento: se descarta como cuerpo.
            i += 2 if i + 1 < len(lines) and lines[i + 1]["bold_ratio"] >= 0.9 else 1
            continue

        if kind in ("parte", "capitulo", "apendices"):
            # El título va en la línea siguiente, en negrita.
            nxt = lines[i + 1]["text"] if i + 1 < len(lines) else ""
            has_title = i + 1 < len(lines) and lines[i + 1]["bold_ratio"] >= 0.9
            title = _title_case_first(nxt) if has_title else ""
            if kind == "parte":
                num = PARTE_RE.match(t).group(1)
                parte_title = f"Parte {num}. {title}".strip(". ")
                capitulo_title = None
            elif kind == "capitulo":
                num = CAPITULO_RE.match(t).group(1)
                capitulo_title = f"Capítulo {num}. {title}".strip(". ")
            else:
                parte_title, capitulo_title = "Apéndices", None
                has_title = False  # "APÉNDICES" no lleva título debajo
            i += 2 if has_title else 1
            continue

        if kind == "apendice":
            num = APENDICE_RE.match(t).group(1)
            has_title = i + 1 < len(lines) and lines[i + 1]["bold_ratio"] >= 0.9
            title = lines[i + 1]["text"] if has_title else ""
            start(Unit(f"RITE:AP{num}", part, f"Apéndice {num}", title,
                       ["Apéndices"], line["page"]))
            i += 2 if has_title else 1
            continue

        if kind == "it_root":
            num, title = IT_ROOT_RE.match(t).groups()
            title, i = _absorb_title(lines, i, title)
            it_titles[num] = f"IT {num}. {_title_case_first(title).rstrip('.')}"
            start(Unit(f"RITE:IT-{num}", part, f"IT {num}", _title_case_first(title),
                       [p for p in [parte_title] if p], line["page"]))
            continue

        if kind == "it":
            raw_num, title = IT_RE.match(t).groups()
            num = re.sub(r"\s", "", raw_num).rstrip(".")
            title, i = _absorb_title(lines, i, title)
            title = _title_case_first(title)
            parents = num.split(".")
            path = [p for p in [parte_title] if p]
            path += [it_titles[".".join(parents[:k])] for k in range(1, len(parents))
                     if ".".join(parents[:k]) in it_titles]
            it_titles[num] = f"IT {num} {title.rstrip('.')}"
            start(Unit(f"RITE:IT-{num}", part, f"IT {num}", title, path, line["page"]))
            continue

        if kind == "articulo":
            num, title = ARTICULO_RE.match(t).groups()
            title, i = _absorb_title(lines, i, title)
            uid = f"{part}:art-{_slug(num)}"
            path = rd_path if part == "RD" else [p for p in [parte_title, capitulo_title] if p]
            start(Unit(uid, part, f"Artículo {num}", title, path, line["page"]))
            continue

        if kind == "disposicion":
            tipo, ordinal, title = DISPOSICION_RE.match(t).groups()
            title, i = _absorb_title(lines, i, title)
            uid = f"{part}:disp-{tipo}-{_slug(ordinal)}"
            path = rd_path if part == "RD" else [p for p in [parte_title, capitulo_title] if p]
            start(Unit(uid, part, f"Disposición {tipo} {ordinal}", title, path, line["page"]))
            continue

    return [u for u in units if u.lines]  # las unidades sin cuerpo solo eran ruta


def split_definitions(unit: Unit) -> list[Unit]:
    """Parte el Apéndice 1 en una unidad por definición.

    Una definición empieza en un párrafo cuya primera línea es "Término: ...".
    El texto anterior a la primera definición queda como introducción.
    """
    out: list[Unit] = []
    intro = Unit(f"{unit.uid}:introduccion", unit.part, f"{unit.label} (introducción)",
                 unit.title, unit.path + [f"{unit.label}. {unit.title}"], unit.page)
    out.append(intro)
    current = intro
    for line in unit.lines:
        m = DEFINICION_RE.match(line["text"]) if _starts_paragraph(line) else None
        if m:
            term = m.group(1).strip()
            short = re.split(r"\s*\(", term)[0].strip()  # sin siglas ni inglés
            current = Unit(f"{unit.uid}:{_slug(short)}", unit.part,
                           f"{unit.label}, definición «{short}»", short,
                           unit.path + [f"{unit.label}. {unit.title}"], line["page"])
            out.append(current)
        current.lines.append(line)
    # Ids únicos aunque se repita un término.
    seen: dict[str, int] = {}
    for u in out:
        if u.uid in seen:
            seen[u.uid] += 1
            u.uid = f"{u.uid}-{seen[u.uid]}"
        else:
            seen[u.uid] = 1
    return [u for u in out if u.lines]


# =============================================================================
# 2. De unidades a chunks
# =============================================================================


def _paragraphs(lines: list[dict]) -> list[tuple[str, bool]]:
    """Agrupa líneas en párrafos. Devuelve (texto, es_tabla).

    Un párrafo de cuerpo empieza con sangría; las líneas de tabla (letra pequeña)
    consecutivas forman un solo bloque, con una fila por línea.
    """
    paras: list[tuple[list[str], bool]] = []
    for line in lines:
        is_table = not _is_body(line)
        if not paras or paras[-1][1] != is_table or (not is_table and _starts_paragraph(line)):
            paras.append(([], is_table))
        paras[-1][0].append(line["text"])
    return [("\n".join(txt) if tab else " ".join(txt), tab) for txt, tab in paras]


def _blocks(paras: list[tuple[str, bool]]) -> list[list[tuple[str, bool]]]:
    """Agrupa párrafos en bloques que conviene no separar.

    Si la unidad tiene apartados numerados ("1. ", "2. "...), cada apartado es un
    bloque con todo lo que le sigue hasta el siguiente. Si no, cada párrafo es
    un bloque.
    """
    if not any(APARTADO_RE.match(p) for p, tab in paras if not tab):
        return [[p] for p in paras]
    blocks: list[list[tuple[str, bool]]] = [[]]
    for p in paras:
        if not p[1] and APARTADO_RE.match(p[0]) and blocks[-1]:
            blocks.append([])
        blocks[-1].append(p)
    return blocks


def _words(text: str) -> int:
    return len(text.split())


def _pack(blocks: list[list[tuple[str, bool]]], max_words: int) -> list[list[tuple[str, bool]]]:
    """Reparte los bloques en trozos de hasta max_words palabras, en orden.

    Un bloque que por sí solo supera el límite se reparte por párrafos; un
    párrafo que lo supera se reparte por frases (o por filas, si es tabla).
    """
    units: list[tuple[str, bool]] = []  # piezas mínimas, ya bajo el límite
    groups: list[list[tuple[str, bool]]] = []
    for block in blocks:
        if sum(_words(p) for p, _ in block) <= max_words:
            groups.append(block)
            continue
        for text, tab in block:
            if _words(text) <= max_words:
                groups.append([(text, tab)])
                continue
            sep = "\n" if tab else " "
            pieces = text.split("\n") if tab else re.split(r"(?<=[.;:])\s+", text)
            buf: list[str] = []
            for piece in pieces:
                if buf and _words(sep.join(buf + [piece])) > max_words:
                    groups.append([(sep.join(buf), tab)])
                    buf = []
                buf.append(piece)
            if buf:
                groups.append([(sep.join(buf), tab)])
    del units
    out: list[list[tuple[str, bool]]] = []
    for g in groups:
        if out and sum(_words(p) for p, _ in out[-1]) + sum(_words(p) for p, _ in g) <= max_words:
            out[-1].extend(g)
        else:
            out.append(list(g))
    return out


def _refs(text: str, part: str, own_id: str) -> list[str]:
    """Referencias cruzadas a artículos e IT del propio Reglamento."""
    if part != "RITE":
        return []  # en el RD, "artículo N" suele referirse a otras normas
    refs = {f"RITE:art-{n}" for n in REF_ARTICULO_RE.findall(text)}
    refs |= {f"RITE:IT-{n}" for n in REF_IT_RE.findall(text)}
    refs.discard(own_id)
    return sorted(refs)


def unit_to_chunks(unit: Unit, doc: str, version: str | None, max_words: int) -> list[Chunk]:
    paras = _paragraphs(unit.lines)
    groups = _pack(_blocks(paras), max_words)
    # En las definiciones el término ya va en la etiqueta: no repetirlo.
    title = unit.title.rstrip(".")
    if unit.title and unit.title in unit.label:
        heading = unit.label
    elif unit.label.startswith("IT "):
        heading = f"{unit.label} {title}"   # "IT 1.1.4.1.2 Temperatura...", como en el RITE
    else:
        heading = f"{unit.label}. {title}"

    
    prefix = " › ".join([doc_label(unit.part)] + unit.path + [heading])
    chunks = []
    for k, group in enumerate(groups, start=1):
        text = "\n".join(p for p, _ in group)
        chunk_id = unit.uid if len(groups) == 1 else f"{unit.uid}#{k}"
        pages = [l["page"] for l in unit.lines if l["page"] is not None]
        chunks.append(Chunk(
            id=chunk_id, doc=doc, version=version, part=unit.part,
            unit=unit.label, title=unit.title, path=unit.path,
            piece=k, pieces=len(groups),
            page_start=min(pages) if pages else unit.page,
            page_end=max(pages) if pages else unit.page,
            has_table=any(tab for _, tab in group) or bool(TABLA_RE.search(text)),
            refs=_refs(text, unit.part, unit.uid),
            n_words=_words(text),
            text=text,
            embed_text=f"{prefix}\n{text}",
        ))
    return chunks


def doc_label(part: str) -> str:
    return "RITE" if part == "RITE" else "RD 1027/2007"


def build_chunks(lines: list[dict], doc: str, version: str | None,
                 max_words: int = MAX_WORDS) -> list[Chunk]:
    """Tubería completa: líneas -> unidades -> chunks."""
    units: list[Unit] = []
    for u in build_units(lines):
        units.extend(split_definitions(u) if u.uid == "RITE:AP1" else [u])
    chunks: list[Chunk] = []
    for u in units:
        chunks.extend(unit_to_chunks(u, doc, version, max_words))
    ids = [c.id for c in chunks]
    duplicated = sorted({i for i in ids if ids.count(i) > 1})
    if duplicated:
        raise ValueError(f"ids de chunk repetidos: {duplicated[:5]}")
    return chunks


# =============================================================================
# 3. Entrada, salida y resumen
# =============================================================================


def print_summary(chunks: list[Chunk]) -> None:
    words = [c.n_words for c in chunks]
    print(f"chunks: {len(chunks)}  (RD: {sum(c.part == 'RD' for c in chunks)}, "
          f"RITE: {sum(c.part == 'RITE' for c in chunks)})")
    print(f"palabras por chunk: mediana {statistics.median(words)}, máx {max(words)}, mín {min(words)}")
    print(f"unidades partidas en varios trozos: {len({c.unit for c in chunks if c.pieces > 1})}")
    print(f"chunks con tabla: {sum(c.has_table for c in chunks)}  ·  con referencias: {sum(bool(c.refs) for c in chunks)}")
    print("ejemplos de id:", ", ".join(c.id for c in chunks[:: max(1, len(chunks) // 8)][:8]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("lines", type=Path, help="ruta al .lines.jsonl de extract.py")
    parser.add_argument("--out-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--max-words", type=int, default=MAX_WORDS)
    args = parser.parse_args()

    with args.lines.open(encoding="utf-8") as f:
        lines = [json.loads(raw) for raw in f]
    meta_path = args.lines.with_name(args.lines.name.replace(".lines.jsonl", ".meta.json"))
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    chunks = build_chunks(lines, meta["doc_id"], meta.get("version"), args.max_words)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.lines.name.replace(".lines.jsonl", "")
    out = args.out_dir / f"{stem}.chunks.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
    print_summary(chunks)
    print(f"escrito en {out}")


if __name__ == "__main__":
    main()
