# Decision log

**English** · [Español](decisions.es.md)

One entry per decision: context, options considered, decision, and how we will know if it was wrong. Newest first.

---

## ADR-004 · Corpus and PDF ingestion: RITE, structure-preserving extraction

**Date:** 2026-11-13 · **Status:** accepted

**Context.** Phase 1 needs one freely available regulation that the author can judge, and an ingestion step that keeps enough structure to cite the exact article. Candidates were the REBT, the telecom infrastructure regulation (ICT) and a CTE basic document.

**Options.**
- Source format: the BOE consolidated PDF, or the consolidated HTML/XML the BOE also publishes, where articles are already tagged.
- Extraction: plain text per page (`page.get_text()`), or text lines with their layout signals (bold, font size, position).

**Decision.** Corpus: the RITE (Royal Decree 1027/2007, `BOE-A-2007-15820`), BOE consolidated text, last amended 2022-08-02. Ingestion from the **PDF** with PyMuPDF, in two stages: `ingest/extract.py` produces clean lines with their layout signals (`bold_ratio`, size, position, printed page) and removes the BOE layout (cover, table of contents, page header, page footer, final legal notice); the chunker (next step) decides the structure. The extractor stops with an error if the start of the body ("TEXTO CONSOLIDADO") is not found, and records the document id, the corpus version and the SHA-256 of the PDF.

**Why.** The PDF is the realistic case: UNE standards, manuals and site documentation only come as PDF, with no structured alternative. Keeping layout signals instead of flattening to text lets the chunker use them; checking the real data showed that article headings carry partial bold (number in bold, title in italics) while technical-instruction headings (IT) do not, so IT headings are detected by regex at the start of the line. Failing fast avoids silently indexing the table of contents, whose title-only lines would outrank the real chunks in retrieval. The version and the hash make it possible to tell whether a change in evaluation results comes from the code or from the corpus.

**Consequences and known limitations.**
- Appendices 4 and 5 (responsible-declaration forms) are images in the PDF: their text is not extracted. Accepted, since they are form templates, not technical requirements.
- The consolidated PDF does not say which later regulation amended each article. The "amends" relations for the knowledge graph (Phase 6) must come from the BOE HTML or its analysis page.
- Tables (8 and 6.5 pt, about 800 lines) are kept as plain text in reading order; their structure is not reconstructed in Phase 1.
- The page-header and footer zones and the patterns are specific to the BOE consolidated layout.
- Validation: 12 tests (`tests/test_extract.py`), 5 unit tests with synthetic data and 7 on the real output (articles 1-47 with no gaps, every IT section with its parent, no BOE layout left, page range 5-96). They check structure, not that every word of the PDF is present.

**How we will know it was wrong.** If evaluation errors in Phase 2 trace back to extraction (lost text, scrambled tables), or if adding a second BOE document means rewriting the patterns, switch the source to the BOE consolidated XML for BOE documents and keep the PDF path for documents that only exist as PDF.

---

## ADR-003 · Conda for the interpreter only, pip + pyproject.toml for dependencies

**Date:** 2026-11-11 · **Status:** accepted

**Context.** The project needs an isolated, reproducible Python environment. The development machine runs Windows with Miniconda and also has an unrelated system Python 3.13 on the PATH. From Phase 3 onwards the application runs in Docker containers, so whatever declares the dependencies locally should also work unchanged inside an image.

**Options.**
- Full conda environment described in `environment.yml`: handles non-Python binaries (CUDA), but Docker images rarely use conda, so dependencies would end up declared twice.
- venv + pip with `pyproject.toml`: the Python standard and exactly what a Dockerfile uses, but it needs an interpreter of the right version first.
- uv with `pyproject.toml` and a lockfile: fast and reproducible out of the box, but one more tool to learn at this stage.

**Decision.** Conda only provides a Python 3.12 interpreter. Every dependency is declared in `pyproject.toml` and installed with pip; nothing is ever installed with `conda install` in this environment. The code lives in a `src/` layout package (`rag_normainst`) installed in editable mode (`pip install -e .`). Python 3.12 rather than the newest release because AI libraries (torch, sentence-transformers, chromadb) lag behind new Python versions.

**Why.** Between the laptop and the container only the source of the interpreter changes (conda locally, the `python:3.12-slim` image in Docker); the dependency declaration and the install command stay the same, so nothing has to be translated. The `src/` layout forces a real install, so packaging mistakes show up locally instead of inside the container.

**Consequences.** `pyproject.toml` declares version ranges, so the local environment and a Docker image built later may resolve different versions; a lockfile will be added in Phase 3. The environment must be activated before installing anything: the first install went to the system Python 3.13 by mistake, which was detected with `sys.executable` and `pip show` and then corrected.

**How we will know it was wrong.** If the Dockerfile needs a second dependency file, or if pinning versions with pip becomes painful in Phase 3, switch to uv, which reads the same `pyproject.toml`.

---

## ADR-002 · Model size constrained by a 4 GB GPU

**Date:** 2026-11-11 · **Status:** accepted

**Context.** The development machine has an NVIDIA GPU with 4 GB of VRAM. Everything runs locally with Ollama.

**Options.**
- 7B model quantized to 4 bits: roughly 4-5 GB, does not fit fully in VRAM. Ollama offloads layers to the CPU and generation slows down noticeably.
- 3-4B model quantized to 4 bits: roughly 2-3 GB, fits fully, leaving some room for the KV cache.

**Decision.** Start with a 3-4B Qwen model in Q4. Keep the embedding model small or medium-sized and allow it to run on CPU during ingestion.

**Consequences.** Fewer retrieved chunks fit in the prompt, so chunking quality and (later) re-ranking matter more. A small model is a weaker LLM-as-a-judge, so automatic evaluation must be calibrated against human judgement.

**How we will know it was wrong.** If answer correctness on the golden set is limited by the generator rather than by retrieval (correct article retrieved, wrong answer), test a larger model or Azure OpenAI through the same OpenAI-compatible client.

---

## ADR-001 · Plain Python first, LangChain afterwards

**Date:** 2026-11-11 · **Status:** accepted

**Context.** The project is a portfolio piece for AI engineering interviews. Credibility comes from explaining the mechanism, not from assembling framework components.

**Options.**
- Start with LangChain to get a working baseline quickly, then rewrite by hand.
- Build the pipeline in plain Python first, measure it, then port it to LangChain.

**Decision.** Plain Python first (Phase 1), evaluation (Phase 2), then a LangChain port (Phase 2B) behind the same `answer(question) -> Answer` interface and the same evaluation script. The LangChain port reuses the hand-written chunker.

**Why not LangChain first.** Its defaults hide exactly the parts that need to be understood: how documents are split, which prompt is actually sent, and how the retriever selects chunks. Starting with them risks copying tutorial code without understanding it.

**How we will know it was wrong.** Phase 2B produces a comparison table (metrics, lines of code, dependencies). If the framework version is clearly better on the golden set with no loss of control, that is recorded here.
