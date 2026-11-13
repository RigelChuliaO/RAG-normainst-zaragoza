"""Inspector visual de la extracción: PDF frente a lo extraído, página a página.

Genera un HTML autocontenido (abrir con doble clic en el navegador) donde cada
página del PDF aparece como imagen con un recuadro encima de cada línea:

  verde    línea conservada (texto normal)
  azul     línea conservada que parece encabezado (Artículo, IT, CAPÍTULO...)
  naranja  línea conservada de tabla (letra de menos de 10 pt)
  rojo     línea descartada (cabecera, pie, preliminares...)
  morado   bloque de imagen (su texto NO se extrae)

A la derecha, el texto extraído de esa página. Al pasar el ratón por una línea
se resalta su recuadro, y al revés.

No modifica nada: lee el PDF y el .lines.jsonl que generó extract.py.
La salida va a data/interim/ (fuera de git): contiene el texto de la norma.

Uso (desde la raíz del repo, con el entorno activado):
  python -m rag_normainst.ingest.inspect_extraction "data/raw/BOE-A-2007-15820-consolidado.pdf"
  python -m rag_normainst.ingest.inspect_extraction "data/raw/....pdf" --pages 28-35
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import re
from pathlib import Path

import pymupdf

from rag_normainst.ingest.extract import DISCLAIMER_RE, FOOTER_RE, HEADER_TEXTS, _line_from_spans

# Patrón para marcar en azul las líneas que parecen encabezado. Es solo una
# ayuda visual: la detección de verdad será trabajo de chunk.py.
HEADING_RE = re.compile(
    r"^(Artículo \d+\.|Artículo único|Disposición |IT \d|CAPÍTULO |PARTE |APÉNDICE|ANEXO|INSTRUCCIÓN TÉCNICA)"
)

# Resolución de las imágenes de página. 100 ppp basta para leer y deja
# el HTML en un tamaño manejable (unos 100 KB por página en JPEG).
DPI = 100


def _key(pdf_page: int, text: str, x0: float, y0: float, x1: float, y1: float) -> tuple:
    """Identifica una línea por página, texto y posición (ya redondeada)."""
    return (pdf_page, text, x0, y0, x1, y1)


def load_kept(lines_path: Path) -> tuple[dict[int, list[dict]], set]:
    """Lee el .lines.jsonl y agrupa las líneas conservadas por página física."""
    by_page: dict[int, list[dict]] = {}
    keys = set()
    with lines_path.open(encoding="utf-8") as f:
        for raw in f:
            l = json.loads(raw)
            by_page.setdefault(l["pdf_page"], []).append(l)
            keys.add(_key(l["pdf_page"], l["text"], l["x0"], l["y0"], l["x1"], l["y1"]))
    return by_page, keys


def classify_kept(text: str, size: float) -> str:
    """Categoría visual de una línea conservada."""
    if size < 10:
        return "table"
    if HEADING_RE.match(text):
        return "heading"
    return "kept"


def drop_reason(text: str) -> str:
    """Motivo probable de descarte, para la etiqueta del recuadro rojo."""
    if text in HEADER_TEXTS:
        return "cabecera"
    if FOOTER_RE.match(text):
        return "pie"
    if DISCLAIMER_RE.match(text):
        return "aviso legal"
    return "preliminares u otro"


def page_boxes(page: pymupdf.Page, kept_keys: set) -> list[dict]:
    """Todos los recuadros de una página: líneas (conservadas o no) e imágenes."""
    boxes = []
    pdf_page = page.number + 1
    data = page.get_text("dict", sort=True)
    for block in data["blocks"]:
        if block["type"] != 0:
            x0, y0, x1, y1 = block["bbox"]
            boxes.append({"cls": "image", "label": "imagen (su texto no se extrae)",
                          "x0": x0, "y0": y0, "x1": x1, "y1": y1, "text": ""})
            continue
        for raw in block["lines"]:
            line = _line_from_spans(raw["spans"], raw["bbox"], pdf_page)
            if line is None:
                continue
            box = {"x0": line.x0, "y0": line.y0, "x1": line.x1, "y1": line.y1, "text": line.text}
            if _key(pdf_page, line.text, line.x0, line.y0, line.x1, line.y1) in kept_keys:
                box["cls"] = classify_kept(line.text, line.size)
                box["label"] = f"conservada · {line.size} pt · negrita {line.bold_ratio}"
            else:
                box["cls"] = "dropped"
                box["label"] = f"descartada · {drop_reason(line.text)}"
            boxes.append(box)
    return boxes


def page_image_b64(page: pymupdf.Page) -> str:
    """Renderiza la página a JPEG y la devuelve en base64 para incrustarla en el HTML."""
    pix = page.get_pixmap(dpi=DPI)
    return base64.b64encode(pix.tobytes("jpeg", jpg_quality=70)).decode("ascii")


def parse_pages(spec: str | None, n_pages: int) -> list[int]:
    """Convierte '28-35' o '5,8,12' en una lista de páginas físicas (desde 1)."""
    if not spec:
        return list(range(1, n_pages + 1))
    pages: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            pages.extend(range(int(a), int(b) + 1))
        else:
            pages.append(int(part))
    return [p for p in pages if 1 <= p <= n_pages]


def build_pages(pdf_path: Path, lines_path: Path, page_numbers: list[int]) -> list[dict]:
    """Prepara los datos de cada página que irán al HTML."""
    kept_by_page, kept_keys = load_kept(lines_path)
    pages = []
    with pymupdf.open(pdf_path) as doc:
        for n in page_numbers:
            page = doc[n - 1]
            kept = kept_by_page.get(n, [])
            boxes = page_boxes(page, kept_keys)
            # Para enlazar cada línea de la lista con su recuadro en la imagen.
            box_index = {(b["text"], b["x0"], b["y0"]): i for i, b in enumerate(boxes)}
            pages.append({
                "pdf_page": n,
                "printed_page": kept[0]["page"] if kept else None,
                "width": page.rect.width,
                "height": page.rect.height,
                "img": page_image_b64(page),
                "boxes": boxes,
                "lines": [
                    {"text": l["text"], "cls": classify_kept(l["text"], l["size"]),
                     "box": box_index.get((l["text"], l["x0"], l["y0"]))}
                    for l in kept
                ],
            })
    return pages


def render_html(pages: list[dict], title: str) -> str:
    """Construye la página HTML. Los datos van como JSON dentro de un <script>."""
    # Escapar "</" evita que un texto del PDF cierre el <script> antes de tiempo.
    data = json.dumps(pages, ensure_ascii=False).replace("</", "<\\/")
    return HTML_TEMPLATE.replace("__TITLE__", html.escape(title)).replace("__DATA__", data)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>Inspector · __TITLE__</title>
<style>
  :root { --kept:#1a9e5a; --heading:#2563eb; --table:#e07b00; --dropped:#d62828; --image:#8b3fd9; }
  * { box-sizing: border-box; }
  body { margin:0; font:14px/1.4 system-ui, sans-serif; color:#1d1d1f; background:#f4f4f2; }
  header { position:sticky; top:0; z-index:5; background:#fff; border-bottom:1px solid #ddd;
           padding:10px 16px; display:flex; gap:14px; align-items:center; flex-wrap:wrap; }
  header h1 { font-size:15px; margin:0 8px 0 0; }
  button, select { font:inherit; padding:4px 10px; border:1px solid #bbb; border-radius:6px; background:#fff; cursor:pointer; }
  .legend label { margin-right:10px; cursor:pointer; white-space:nowrap; }
  .sw { display:inline-block; width:11px; height:11px; border:2px solid; margin-right:4px; vertical-align:-1px; }
  main { display:grid; grid-template-columns:minmax(0,1.1fr) minmax(0,1fr); gap:16px; padding:16px; }
  .pagewrap { position:relative; background:#fff; box-shadow:0 1px 4px rgba(0,0,0,.15); align-self:start; }
  .pagewrap img { display:block; width:100%; }
  .pagewrap svg { position:absolute; inset:0; width:100%; height:100%; }
  rect { fill:transparent; stroke-width:1; }
  rect.kept{stroke:var(--kept)} rect.heading{stroke:var(--heading);stroke-width:1.6}
  rect.table{stroke:var(--table)} rect.dropped{stroke:var(--dropped);stroke-dasharray:3 2}
  rect.image{stroke:var(--image);stroke-width:1.6;fill:rgba(139,63,217,.08)}
  rect.hl { fill:rgba(255,220,0,.45); stroke-width:2.2; }
  .hidden { display:none; }
  .side { background:#fff; border:1px solid #ddd; border-radius:8px; padding:10px 12px; max-height:calc(100vh - 90px); overflow:auto; }
  .stats { font-size:13px; color:#555; margin-bottom:8px; }
  ol { margin:0; padding-left:2.6em; }
  li { padding:2px 4px; border-left:3px solid transparent; cursor:default; }
  li.kept{border-color:var(--kept)} li.heading{border-color:var(--heading);font-weight:600}
  li.table{border-color:var(--table);font-size:12.5px;color:#444} li.hl{background:#fff3b0}
  #tip { position:fixed; pointer-events:none; background:#222; color:#fff; font-size:12px; padding:4px 8px;
         border-radius:4px; display:none; max-width:420px; z-index:10; }
</style></head><body>
<header>
  <h1>__TITLE__</h1>
  <button id="prev">◀</button><select id="sel"></select><button id="next">▶</button>
  <span class="legend">
    <label><input type="checkbox" data-c="kept" checked><span class="sw" style="border-color:var(--kept)"></span>conservada</label>
    <label><input type="checkbox" data-c="heading" checked><span class="sw" style="border-color:var(--heading)"></span>encabezado</label>
    <label><input type="checkbox" data-c="table" checked><span class="sw" style="border-color:var(--table)"></span>tabla</label>
    <label><input type="checkbox" data-c="dropped" checked><span class="sw" style="border-color:var(--dropped)"></span>descartada</label>
    <label><input type="checkbox" data-c="image" checked><span class="sw" style="border-color:var(--image)"></span>imagen</label>
  </span>
  <span style="color:#777;font-size:12px">flechas ← → para cambiar de página</span>
</header>
<main>
  <div class="pagewrap"><img id="img" alt=""><svg id="svg" preserveAspectRatio="none"></svg></div>
  <div class="side"><div class="stats" id="stats"></div><ol id="list"></ol></div>
</main>
<div id="tip"></div>
<script>
const PAGES = __DATA__;
const hiddenCls = new Set();
let cur = 0;
const $ = id => document.getElementById(id);
const tip = $("tip");

PAGES.forEach((p, i) => {
  const o = document.createElement("option");
  o.value = i;
  o.textContent = "pág. PDF " + p.pdf_page + (p.printed_page ? "  (impresa " + p.printed_page + ")" : "");
  $("sel").appendChild(o);
});

function esc(s) { return s.replace(/&/g,"&amp;").replace(/</g,"&lt;"); }

function highlight(i, on) {
  const r = document.querySelector('rect[data-i="' + i + '"]');
  if (r) r.classList.toggle("hl", on);
  document.querySelectorAll('li[data-box="' + i + '"]').forEach(li => li.classList.toggle("hl", on));
}

function show(i) {
  cur = Math.max(0, Math.min(PAGES.length - 1, i));
  const p = PAGES[cur];
  $("sel").value = cur;
  $("img").src = "data:image/jpeg;base64," + p.img;
  const svg = $("svg");
  svg.setAttribute("viewBox", "0 0 " + p.width + " " + p.height);
  svg.innerHTML = p.boxes.map((b, k) =>
    '<rect data-i="' + k + '" class="' + b.cls + (hiddenCls.has(b.cls) ? " hidden" : "") +
    '" x="' + b.x0 + '" y="' + b.y0 + '" width="' + (b.x1 - b.x0) + '" height="' + (b.y1 - b.y0) + '"></rect>'
  ).join("");
  const count = c => p.boxes.filter(b => b.cls === c).length;
  $("stats").textContent = "Conservadas: " + p.lines.length + " · descartadas: " + count("dropped") +
    " · imágenes: " + count("image") + " · de tabla: " + count("table");
  $("list").innerHTML = p.lines.map(l =>
    '<li class="' + l.cls + '" data-box="' + (l.box ?? "") + '">' + esc(l.text) + "</li>").join("");
}

$("svg").addEventListener("mousemove", e => {
  const r = e.target.closest("rect");
  if (!r) { tip.style.display = "none"; return; }
  const b = PAGES[cur].boxes[r.dataset.i];
  tip.textContent = b.label + (b.text ? " — " + b.text : "");
  tip.style.display = "block";
  tip.style.left = (e.clientX + 14) + "px";
  tip.style.top = (e.clientY + 14) + "px";
});
$("svg").addEventListener("mouseover", e => { const r = e.target.closest("rect"); if (r) highlight(r.dataset.i, true); });
$("svg").addEventListener("mouseout", e => { const r = e.target.closest("rect"); if (r) highlight(r.dataset.i, false); tip.style.display = "none"; });
$("list").addEventListener("mouseover", e => { const li = e.target.closest("li"); if (li && li.dataset.box) highlight(li.dataset.box, true); });
$("list").addEventListener("mouseout", e => { const li = e.target.closest("li"); if (li && li.dataset.box) highlight(li.dataset.box, false); });

document.querySelectorAll(".legend input").forEach(cb => cb.addEventListener("change", () => {
  cb.checked ? hiddenCls.delete(cb.dataset.c) : hiddenCls.add(cb.dataset.c);
  show(cur);
}));
$("prev").onclick = () => show(cur - 1);
$("next").onclick = () => show(cur + 1);
$("sel").onchange = e => show(+e.target.value);
document.addEventListener("keydown", e => {
  if (e.key === "ArrowLeft") show(cur - 1);
  if (e.key === "ArrowRight") show(cur + 1);
});
show(0);
</script></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pdf", type=Path, help="ruta al PDF consolidado del BOE")
    parser.add_argument("--interim-dir", type=Path, default=Path("data/interim"),
                        help="carpeta con el .lines.jsonl, donde también se escribe el HTML")
    parser.add_argument("--pages", help="páginas físicas a incluir, p. ej. '28-35' o '5,8,96' (por defecto, todas)")
    args = parser.parse_args()

    lines_path = args.interim_dir / f"{args.pdf.stem}.lines.jsonl"
    if not lines_path.exists():
        raise SystemExit(f"No existe {lines_path}: ejecuta antes extract.py sobre este PDF")

    with pymupdf.open(args.pdf) as doc:
        page_numbers = parse_pages(args.pages, doc.page_count)

    pages = build_pages(args.pdf, lines_path, page_numbers)
    out = args.interim_dir / f"{args.pdf.stem}.inspect.html"
    out.write_text(render_html(pages, args.pdf.name), encoding="utf-8")
    size_mb = out.stat().st_size / 1e6
    print(f"Inspector escrito en {out} ({len(pages)} páginas, {size_mb:.1f} MB). Ábrelo en el navegador.")


if __name__ == "__main__":
    main()
