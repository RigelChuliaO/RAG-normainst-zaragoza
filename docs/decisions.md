# Decision log

**English** · [Español](decisions.es.md)

One entry per decision: context, options considered, decision, and how we will know if it was wrong. Newest first.

---

## ADR-008 · Evaluation: golden set by unit, code-based grading first, LLM judge only as an alarm

**Date:** 2026-11-18 · **Status:** accepted

**Context.** Phase 2 needs numbers that stay comparable across prompt, chunking and model changes. The generator and the only local judge are 4B models.

**Options.**
- Grade answers with an LLM judge only (common in tutorials).
- Grade with deterministic code checks (required facts, forbidden facts, «No consta», citations) and use a judge for faithfulness, which code cannot check.
- Compare retrieval by chunk id, or by regulation unit (article, technical instruction, definition).

**Decision.**
- 42-question golden set (`eval/golden_set.jsonl`) with expected **units**, so it survives chunking changes; 6 unanswerable questions; 8 held out.
- Retrieval and generation are measured separately. Each generation failure is diagnosed as a retrieval failure (the required facts never reached the model) or a generation failure.
- The official grade is the code-based one (`correct`, `complete`). The LLM judge (`judge.py`) is used as an alarm for unfaithful answers, not as the grade.

**Why.** Calibrating the judge (qwen3:4b-instruct) on its 30 answers gave 28/30 agreement and Cohen's kappa 0.71, but it let 2 of 5 unfaithful answers through, including q30 («Yes, you can install a coal boiler in a new house»), the most dangerous kind of error. It catches off-topic claims and misses conclusions drawn from the absence of a rule and over-generalisations. It also grades its own model's answers. Caveat: the reference labels were written by Claude, not by a domain expert, because the judge's verdicts were seen before labelling.

**How we will know it was wrong.** If a stronger or different judge (a larger local model, or Azure OpenAI through the same client) reaches kappa ≥ 0.6 with no unfaithful answer let through on a human-labelled sample, the judge can become part of the grade.

---

## ADR-007 · Generator: qwen3:4b-instruct through Ollama, with a citation-only prompt

**Date:** 2026-11-16 · **Status:** accepted (to be confirmed by the Phase 2 evaluation)

**Context.** ADR-002 chose a 3-4B Qwen model in Q4. In Ollama, the `qwen3:4b` tag is now the *Thinking-2507* variant: it always reasons before answering, emits a lone `</think>`, and `--think=false` does not turn it off. With about 2 GB of free VRAM, the model loads split between CPU and GPU, with a 4096-token context window.

**Options.** `qwen3:4b` (thinking), `qwen3:4b-instruct` (Instruct-2507, no reasoning), `qwen3:1.7b` (hybrid, reasons by default).

**Decision.** Use **`qwen3:4b-instruct`** at temperature 0 through the OpenAI-compatible endpoint (`/v1`) with the `openai` client. The prompt numbers the fragments `[1]…[k]`; the model only writes those labels and the code turns them into citations from the chunk metadata, so the model cannot invent an article number. If the fragments do not contain the answer, it must reply exactly "No consta en el RITE.". Questions that name an IT or an article fetch that chunk by id first (fixes golden-seed q04). If the prompt fills the 4096-token window, the code stops with an error instead of letting Ollama truncate silently.

**Evidence** (4 manual questions, warm model).
| | qwen3:4b-instruct | qwen3:1.7b |
| --- | --- | --- |
| "What is the RITE?" | correct, cites Art. 1 (without RAG it invented a decree) | – |
| Winter operative temperature | correct (21–23 °C, IT 1.1.4.1.2), but omits humidity and IT 3.8 | mixes IT 3.8 with design data, **no citation**, 571 output tokens |
| "What does IT 1.2.4.7.4 say?" | correct, found by id lookup | – |
| Cable cross-section (not in the RITE) | "No consta" | "No consta" (332 tokens of reasoning) |
| Generation time | 12–21 s (~110 prompt tok/s, ~20 output tok/s) | 12–20 s |

The 1.7b model is not faster end to end, because its reasoning tokens cancel out its speed, and it breaks the citation rule. The 4b-instruct model is faithful but sometimes incomplete; asking for "concise but complete" answers did not fix that.

**How we will know it was wrong.** If Phase 2 shows answers that are faithful but miss conditions present in the retrieved fragments (completeness), try few-shot examples in the prompt, fewer and better-ranked fragments (re-ranking, Phase 5), or a larger model through the same client.

---

## ADR-006 · Embedding model: multilingual-e5-base first, compared with e5-small and bge-m3

**Date:** 2026-11-14 · **Status:** accepted (to be confirmed by the Phase 2 evaluation)

**Context.** The embedding model turns each chunk and each question into a vector. It must handle Spanish, fit the chunks in its window, and run on the CPU: the GPU is a GTX 1650 with 4 GB, of which about 2 GB are already used by the Windows desktop, and the rest is reserved for the LLM (ADR-002).

**Options** (figures from the Hugging Face model cards).
- `intfloat/multilingual-e5-small`: 384 dimensions, 512-token window, requires `query: ` / `passage: ` prefixes. Fastest.
- `intfloat/multilingual-e5-base`: 768 dimensions, 512-token window, same prefixes.
- `BAAI/bge-m3`: 568M parameters, 1024 dimensions, 8192-token window, no prefixes, also produces sparse (lexical) vectors.
- Rejected: `paraphrase-multilingual-MiniLM-L12-v2`, common in tutorials, because its 128-token window would truncate most chunks.

**Decision.** Start with **multilingual-e5-base** on the CPU, through `sentence-transformers`. Keep e5-small and bge-m3 as candidates to compare with the Phase 2 golden set. The model-specific details (name, prefixes, window) live in one place, `embeddings.py`, so switching models is one argument.

**Why.** With 389 chunks, indexing on the CPU is a one-off cost of minutes; what repeats is embedding each question, and a ~278M-parameter model does it in a fraction of a second on the CPU. e5-base is a better model than e5-small without the size of bge-m3. Its required prefixes are a classic silent failure worth handling explicitly.

**Risk.** The 512-token window: chunks are limited to 300 words plus the path prefix (ADR-005), and Spanish uses more tokens per word than English. The chunks are measured with the model's own tokenizer before indexing; if many exceed the window, either lower the word limit or switch to bge-m3.

**How we will know it was wrong.** If Phase 2 shows that bge-m3 retrieves clearly better on the golden set, or that e5-small is just as good and faster, the comparison table goes in the README and this decision is updated.

---

## ADR-005 · Structure-aware chunking of the RITE

**Date:** 2026-11-13 · **Status:** accepted

**Context.** The chunk is the unit that becomes a vector, is retrieved, is read by the LLM and is cited. The RITE has 228 headed units: median 110 words, 32 above roughly 400 words (more than fits in 512 tokens), 34 headings with no text of their own, and several units with tables.

**Options.** Fixed size with overlap; recursive splitting on separators; semantic chunking; structure-aware chunking; hierarchical (parent-child) chunking.

**Decision.** Structure-aware chunking (`ingest/chunk.py`):
- One chunk per article, provision, IT section with its own text and definition in Appendix 1; one per appendix for the rest.
- Headings with no text of their own (Part, Chapter, parent IT sections) only contribute their title to the path of their children.
- Long units are split at their numbered paragraphs ("1.", "2.") and, if that is not enough, at paragraph boundaries, up to a limit of **250 words** (initially 300; see the measurement below). Each piece gets its own id (`#1`, `#2`) and the full path. Different units are never merged.
- Tables stay inside their section (`has_table`).
- Each chunk keeps `text` (the body, for the prompt) and `embed_text` (path of titles + body, for the embedding).
- Deterministic, readable ids: `RITE:art-2`, `RITE:IT-1.1.4.1.2`, `RITE:AP1:aire-de-expulsion`.

**Why.** It is the unit the regulation itself uses and the one people cite: one chunk = one unit of meaning = one citation. The path prefix gives context to the 42 very short units without duplicating content as an overlap would. Stable ids make the Phase 2 golden set possible.

**Result.** 417 chunks (median 109 words, maximum 250); 58 units split into pieces; 106 definitions (plus the appendix introduction); 26 chunks with tables. All 47 articles and all 130 leaf IT sections have a chunk. All body text is preserved (49,780 words in units = in chunks), and two runs produce the same file. Layout signals used: a new paragraph is indented (x0 ≈ 107.7) and a continuation line is not (x0 ≈ 90.7), which also joins headings that wrap onto a second line.

**Consequences and known limitations.**
- **Measured in tokens (2026-11-14).** With 300 words, 7 of 389 chunks exceeded the 512-token window of multilingual-e5-base (up to 564 tokens): the Appendix 2 list of UNE standards (codes cost about 1.9 tokens per word, against 1.41 on average) and deep IT sections whose title path takes up to 96 tokens. The limit was lowered to 250 words. The word limit is only a cheap proxy: the guarantee is a check at indexing time with the model's own tokenizer, which stops with an error if any chunk does not fit instead of truncating silently.
- The path prefix is long for deep IT sections (about 40 words): it uses a noticeable share of the window. If it hurts, keep only the last levels.
- Tables are plain text with one cell per line: an LLM can read them, but a question about a specific value may not retrieve them well.
- When a numbered paragraph is longer than the limit, a list ("a), b)…") can be separated from its lead-in sentence.
- Cross-references (`refs`) are detected with approximate patterns, only inside the Regulation. They are not used until Phase 6.

**How we will know it was wrong.** If retrieval in Phase 2 fails on questions whose answer needs the parent's or neighbouring sections' context, try hierarchical chunking. If questions about table values fail, rebuild tables as rows of text ("Summer: operative temperature 23…25 °C, relative humidity 45…60 %").

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
