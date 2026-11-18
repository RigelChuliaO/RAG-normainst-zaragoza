# Technical Regulations Assistant (RAG)

Ask questions in natural language about Spanish technical installation regulations and get answers that **cite the exact article** they rely on, so every answer can be verified. Everything runs locally: documents never leave the machine.

> Status: Phase 1 — minimal RAG in plain Python works end to end. See [`docs/plan.md`](docs/plan.md) for the roadmap.

## Why this domain

Regulations have explicit structure: articles reference other articles, documents amend earlier ones, requirements apply to specific building or installation types. That makes them a textbook case for structure-aware chunking, hybrid search and, later, a knowledge graph. The author is a telecommunications engineer with on-site experience, so answers can be judged by someone who knows the domain.

## Architecture

_Diagram to be added in Phase 1._

Ingestion: PDF (public BOE text) → text extraction → article-level chunking → embeddings → vector store.
Query: question → query embedding → top-k similarity search → prompt assembly → local LLM (Ollama) → answer with article citations.

## How to run

_Target from Phase 3 onwards: a single `docker compose up`._

### Development setup

Requires Git and Miniconda (or any Python 3.12 installation).

```bash
conda create -n rag-normainst python=3.12
conda activate rag-normainst
python -m pip install -e .
cp .env.example .env    # Windows: copy .env.example .env
```

Check that the package is installed in the active environment:

```bash
python -c "import rag_normainst; print(rag_normainst.__file__)"
```

The printed path should point to `src/rag_normainst/__init__.py` inside this repository.

### Build the index and ask a question

Download the consolidated RITE from the BOE (BOE-A-2007-15820) into `data/raw/`. It is not stored in this repository. Install [Ollama](https://ollama.com) and pull the generator: `ollama pull qwen3:4b-instruct`.

```bash
python -m rag_normainst.ingest.extract data/raw/BOE-A-2007-15820-consolidado.pdf
python -m rag_normainst.ingest.chunk data/interim/BOE-A-2007-15820-consolidado.lines.jsonl
python -m rag_normainst.store data/processed/BOE-A-2007-15820-consolidado.chunks.jsonl
python -m rag_normainst.pipeline "¿Qué temperatura operativa se exige en invierno?"
```

Example output:

```
21...23 ºC [1]

fuentes:
  [1] RITE, IT 1.1.4.1.2. Temperatura operativa y humedad relativa (pág. 29)
```

The model only writes the label `[1]`; the article, title and page come from the chunk metadata, so a citation always points to a real fragment. If the retrieved fragments do not contain the answer, the reply is "No consta en el RITE." Run the tests with `python -m pip install -e ".[dev]"` and `python -m pytest`.

## Evaluation results

Baseline v0, measured on 16-17 November 2026 with `eval/run_eval.py` on a 42-question golden set (`eval/golden_set.jsonl`: 36 answerable, 6 whose answer is not in the RITE, 8 held out). Embeddings `multilingual-e5-base`, k = 5, generator `qwen3:4b-instruct`. Retrieval and generation are measured separately ([ADR-008](docs/decisions.md)).

| Pipeline | Hit rate@5 | Recall@5 | MRR | Correct | Complete | Faithful (judge) | Invents when the answer is absent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Plain Python (v0) | 0.86 | 0.85 | 0.70 | 0.76 | 0.74 | 0.90 (0.83 by reference labels) | 0 / 6 |
| LangChain port | – | – | – | – | – | – | – |

- **Correct / complete** are graded by code: required facts present, no forbidden facts, «No consta» exactly when it should; *complete* also requires citing every expected unit.
- **Faithful** is the LLM judge's rate on the 30 answers that claim something. The judge agreed with the reference labels on 28/30 (Cohen's kappa 0.71) but let 2 unfaithful answers through, so it is used as an alarm, not as the grade.
- Of the 10 failures, 7 are retrieval failures (the required facts never reached the model) and 3 are generation failures.
- Weakest point: prohibitions (1 of 4 correct). User wording («coal boiler», «storage room») does not match the regulation's («fossil solid fuels», «non-habitable rooms»); hit@10 equals hit@5, so a larger k does not help. When the right fragment is missing, the model does not say «No consta»: it answers «Yes, you can» from unrelated fragments (q28-q30).

Reproduce: `python eval/run_eval.py --pipeline pure` (retrieval) and `python eval/run_eval.py --pipeline pure --stage generation` (needs Ollama). Dated results are kept in `eval/results/`.

## Design decisions

Every significant choice and its reasoning is recorded in [`docs/decisions.md`](docs/decisions.md).

## Data and copyright

No regulation PDFs are stored in this repository. BOE texts are freely accessible and can be downloaded by the user; UNE standards are copyrighted and are not part of the corpus. At most, a small sample of freely available text is included under `data/sample/` for testing.
