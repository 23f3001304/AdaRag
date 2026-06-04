# AdaRag — Adaptive Multimodal RAG

Most RAG pipelines assume one document type and one ingestion strategy: fixed chunks, embed,
top-k. That breaks on a mixed corpus. AdaRag **profiles every file** — modality first, structure
second — and routes it to the right preprocessing and chunking path, into a single hybrid index
that retrieves across papers, code, notes, images, audio, and video. The pipeline then **tunes
itself** against a cost-aware objective.

Full design: [DESIGN.md](DESIGN.md).

> **Status:** Phase 0 (scaffold + baseline). Built incrementally, one phase at a time, each gated
> by a measurable result on the eval set.

## Roadmap

| Phase | Builds | Gate |
|---|---|---|
| 0 | Infra + BYOK providers + one text file end-to-end (naive chunk, dense retrieval, generated answer) | end-to-end answer |
| 1 | Hybrid (sparse + RRF) + cross-encoder rerank + eval harness | baseline metrics locked |
| 2 | Text enrichment (contextual prefix, entities, keyphrases) | measured recall lift |
| 3 | Adaptive ingestion (profiler, code AST, paper sections, notes) | measured lift |
| 4 | Multimodal (audio, image, video, PDF figures), originals preserved | modality coverage |
| 5 | Optuna multi-objective self-tuning + feedback logging | Pareto front + adopted config |
| 6 | Next.js frontend (routing + retrieval traces, optimizer dashboard) | visible decisions |

## Stack

- **Embeddings:** bge-m3 (local, dense + sparse from one model)
- **Vector store:** Qdrant (native hybrid, payload filters, on-disk)
- **Reranker:** bge-reranker-v2-m3
- **Providers (BYOK):** Anthropic, OpenAI, Ollama
- **Backend:** FastAPI (async), Postgres (metadata, feedback, eval runs)
- **Tuning / eval:** Optuna, RAGAS
- **Infra:** Docker Compose (Qdrant, Postgres, API, web)
- **Tooling:** uv, Python 3.12

## Repo layout

```
api/           FastAPI app
core/          pipeline core, layer interfaces
providers/     BYOK: anthropic, openai, ollama, local embeddings
profiling/     heuristic + classifier profiler
ingestion/     multimodal preprocessors
chunking/      adaptive chunkers + registry
enrichment/    contextual prefix, metadata
index/         qdrant hybrid index
retrieval/     hybrid retrieval + query rewrite
rerank/        cross-encoder
evaluation/    datasets, metrics, ragas
optimization/  optuna sweep
web/           Next.js (phase 6)
```

## Quickstart

Coming together as Phase 0 lands. Will be: copy `.env.example` → `.env`, add a provider key,
`docker compose up`.
