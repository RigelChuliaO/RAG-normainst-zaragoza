# Decision log

One entry per decision: context, options considered, decision, and how we will know if it was wrong. Newest first.

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
