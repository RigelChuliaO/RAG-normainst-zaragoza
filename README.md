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

_Baseline to be published in Phase 2._

| Pipeline | Hit rate@k | Recall@k | MRR | Faithfulness |
| --- | --- | --- | --- | --- |
| Plain Python (v0) | – | – | – | – |
| LangChain port | – | – | – | – |

## Design decisions

Every significant choice and its reasoning is recorded in [`docs/decisions.md`](docs/decisions.md).

## Data and copyright

No regulation PDFs are stored in this repository. BOE texts are freely accessible and can be downloaded by the user; UNE standards are copyrighted and are not part of the corpus. At most, a small sample of freely available text is included under `data/sample/` for testing.
