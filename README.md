# Technical Regulations Assistant (RAG)

Ask questions in natural language about Spanish technical installation regulations and get answers that **cite the exact article** they rely on, so every answer can be verified. Everything runs locally: documents never leave the machine.

> Status: Phase 0 — repository skeleton. See [`docs/plan.md`](docs/plan.md) for the roadmap.

## Why this domain

Regulations have explicit structure: articles reference other articles, documents amend earlier ones, requirements apply to specific building or installation types. That makes them a textbook case for structure-aware chunking, hybrid search and, later, a knowledge graph. The author is a telecommunications engineer with on-site experience, so answers can be judged by someone who knows the domain.

## Architecture

_Diagram to be added in Phase 1._

Ingestion: PDF (public BOE text) → text extraction → article-level chunking → embeddings → vector store.
Query: question → query embedding → top-k similarity search → prompt assembly → local LLM (Ollama) → answer with article citations.

## How to run

_To be added in Phase 1. Target from Phase 3 onwards: a single `docker compose up`._

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
