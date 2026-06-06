# AdaRag

Adaptive multimodal RAG. Drop in text, code, images, audio, or video; AdaRag profiles each file,
routes it down the right preprocessing path, indexes the result in a single hybrid vector store,
and answers questions over the corpus with citations to the artifacts it grounded in. A chat
surface, an ingest disambiguation flow, a per-chat agent mode, a Pareto-front Optuna optimizer,
and a stacked notification center sit on top.

The project is a single-user system: it runs on one workstation, owns its data, and routes
multimodal work through the local CLIs (claude-cli, gemini-cli) and a local Ollama install so a
free tier is genuinely usable.

---

## What it does, in one paragraph

You upload a file. AdaRag detects the modality and converts it into a text surrogate -
vision-captioned + OCR'd for an image, transcribed for audio / video, parsed for a PDF. The text
is chunked adaptively (code AST, paper-section, naive prose), every chunk gets a situating context
and a small bag of entities / dates / keyphrases from a fast LLM call, and the result lands in a
Qdrant collection with named dense + sparse vectors. If the file is ambiguous (a photo of "a young
man" with no name, a document that never names its subject), the model files clarification
questions for you to answer on the Ingest tab; answering retags the document so it becomes
findable by the entity you supplied.

You ask a question. Hybrid retrieval + cross-encoder rerank narrows to the top-k; the answer
prompt is built with citations and (when the cited hit is an image or video) the original media
is attached so a vision-capable model sees the pixels, not just the text caption. The answer
streams back as SSE deltas, with thinking, tool-use cards (in agent mode), and citation chips.

---

## Architecture

Three processes, plus the data stores.

```
+---------------------------+
|   Next.js frontend :3000  |  React 19, Tailwind v4, motion. Streams SSE from /api/*.
+--------------+------------+
               | /api/* proxied to backend
+--------------v------------+
|   FastAPI api (docker)    |  Ingest, chat, query, route, clarifications, files, optimizer.
|                           |  Talks to Qdrant + Postgres + the host bridge.
+--------------+------------+
               | http://host.docker.internal:8088
+--------------v------------+
|   Host CLI bridge :8088   |  uvicorn process on the host. Owns claude-cli, gemini-cli,
|   (scripts/run_bridge.py) |  Ollama. Exposes /generate, /stream, /vision, /config, /models.
+---------------------------+

+----------+   +-----------+   +-------------------+
|  Qdrant  |   | Postgres  |   |  data/uploads/    |
|  vectors |   | metadata  |   |  preserved files  |
+----------+   +-----------+   +-------------------+
```

The api container can't exec the host's CLI shims; the bridge runs on the host where those CLIs
own their auth, and proxies them over HTTP. This means a free Claude subscription works for chat,
and Ollama works for cheap enrichment.

---

## Pipeline

**Ingest** (`POST /ingest`):

1. The file is saved under `data/uploads/<uuid>.<ext>` and handed to a modality-specific
   preprocessor (`ingestion/`): vision caption + OCR for images, Whisper-style transcript for
   audio / video, native text for PDF / markdown / code.
2. The text surrogate is chunked by an adaptive chunker (`chunking/registry.py` picks code-AST,
   paper-section, or naive based on the profile).
3. Each chunk gets two LLM enrichments in parallel (capped concurrency):
   - `ContextualEnricher.context_for(chunk, document, attach=path)` writes a maximally dense
     situating context. When the file is an image / video, the original media is attached via
     `@<path>` so a vision-capable LLM grounds the context in pixels.
   - `MetadataEnricher.extract(chunk, attach=path)` returns entities / dates / keyphrases as JSON.
4. Each chunk is embedded with bge-m3 (dense + sparse from one model) and upserted to Qdrant under
   `adarag_chunks` (or a bucket-suffixed collection). The Postgres `Document` + `Chunk` rows are
   inserted in the same transaction so a refresh sees the file immediately.
5. As a background task, `AmbiguityDetector.analyze(text, modality, entities, attach=path)` asks
   the model what's unclear about the file. Each question becomes a row in `clarifications`. The
   Ingest tab polls these and shows them one at a time as a poll-style flow.

**Answer** (`POST /chat/stream`, `POST /query`):

1. The bucket's `HybridRetriever` runs dense + sparse `prefetch` queries and lets Qdrant fuse them
   with server-side RRF; up to 20 candidates come back.
2. `CrossEncoderReranker` (bge-reranker-v2-m3, GPU when available) scores the whole pool against
   the query; the top-k by relevance is kept. `_diversify` guarantees every retrieved media
   modality lands its best chunk in the context so a text-only top-k can't bury the photo.
3. `_build` assembles the answer prompt. The chunk's `text` (which `retag_document` prepends with
   any user-applied facts like "This is Hemang.") goes in as citation context. Image / video
   originals are attached via `@<path>` so vision-capable LLMs see them.
4. The prompt is sent to the chosen LLM. Stream-json deltas (text, thinking, tool_use, tool_result)
   are parsed by `providers/cli_stream.py` and re-emitted as SSE events. The chat orchestrator
   wraps them with a `query` event up front and a `done` event with citations at the end.
5. Each answer runs as a server-side `ChatJob` decoupled from the SSE connection. The buffer is
   checkpointed to Postgres every 600 ms, so a refresh, container restart, or mid-stream crash
   never loses an answer - on reconnect the api replays the buffer then streams the rest.

---

## Notable features

**Bucket isolation.** Every bucket maps to its own Qdrant collection (`adarag_chunks_<slug>`) and
its own per-bucket `BucketServices` (ingest / answer / chat). Shared collaborators (embedder,
reranker, chunker, LLM) are constructed once at startup.

**Clarifications.** At ingest, the model judges if a file's subject is identifiable. Ambiguous
files (an unnamed photo, a document about an unnamed subject) yield up to four distinct questions
with candidate answers drawn from the bucket's known entities and filtered by the LLM. The Ingest
tab presents these as a poll-style stack; answering retags the file's chunks by prepending the
fact to chunk text AND adding it to entities AND appending it to the situating context, then
re-embeds. A re-ingest of the same source drops stale pending questions instead of stacking on.

**Per-chat agent mode.** A `⚡ agent` pill in the chat header opts a chat into tool use. When on,
the bridge invokes claude-cli (or gemini-cli) with `--allowed-tools` (or `--yolo`), and the
stream's `tool_use` + `tool_result` events render as inline wrench cards in the assistant turn -
click to expand the JSON input and the result. Approve / deny scaffolding is built and dormant
because neither CLI currently exposes a plug-in permission gate in print mode; the design moves
to the Anthropic / Google SDK direct path when we want real pre-approval (the trade-off is
agent-mode billing through the API instead of a subscription).

**Per-chat answer scope.** A three-state pill (`strict | medium | lazy`) picks which answer
prompt the LLM gets. Strict refuses anything not in the retrieved context. Medium allows general
knowledge with a `(general knowledge)` marker. Lazy is open - context, general knowledge, and
tools are all in play.

**Chat resume.** Every chat answer is a server-side `ChatJob` with a Postgres `ChatJobRow` row.
The browser holds only a `messageId` and a `pending: true` flag on the assistant turn. On reload
the page hits `GET /chat/stream/{id}` which replays the buffered output and streams the rest.
Snapshots every 600 ms mean even an api crash mid-stream leaves the partial answer + an
"interrupted" marker; a Continue button retries.

**Media attachment.** Image and video originals are attached to the answer prompt for vision-
capable LLMs (claude-cli, gemini-cli) so the model sees the actual pixels, not just our text
caption. Same `@<path>` mechanism is used at ingest time for context / metadata / ambiguity
enrichment when the bridge's chosen LLM supports vision.

**Optimizer.** An Optuna multi-objective study sweeps `rerank_candidates` and other knobs against
the relevance / latency Pareto front using golden queries built from the active bucket. A live
trial scatter + headline runs on the Optimizer tab.

**Stop is real.** The Stop button fires `POST /chat/stop/{id}` which `cancel()`s the asyncio
task; the bridge's `_stream_lines` finally-clause kills the claude-cli / gemini-cli subprocess.
The partial buffer stays in the saved chat as history, and a Continue button reissues.

**Stacked notification center.** Bottom-right peek that fans out on hover, holding the
clarification nudge plus transient success / info / error toasts. Decoupled from the React tree -
any code can dispatch `adarag:notify` events.

---

## Stack

- **Backend:** FastAPI on Python 3.12 (`uv` for tooling), SQLAlchemy 2 async over asyncpg,
  background tasks for non-blocking ingest detection.
- **Embeddings:** BAAI/bge-m3 local (dense + sparse from one model, GPU when available).
- **Vector store:** Qdrant 1.x with named dense + sparse vectors and server-side RRF prefetch.
- **Reranker:** BAAI/bge-reranker-v2-m3 cross-encoder over the full candidate pool per query.
- **LLM providers:** routed through the bridge: claude-cli (Sonnet / Opus / Haiku), gemini-cli
  (2.5-flash / 2.5-pro), Ollama (qwen3:8b-q8_0 default for free local enrichment). All accessed
  via the `cli-bridge` provider in api config.
- **Frontend:** Next.js 16 (App Router + Turbopack), React 19, Tailwind v4. JetBrains Mono +
  Bricolage Grotesque + Hanken Grotesk fonts. `recharts` for the optimizer, `motion` for
  transitions, `react-markdown` + `react-syntax-highlighter` for chat. SSE consumed via
  `ReadableStream.getReader()` with a streaming JSON delta parser.
- **Infra:** Docker Compose runs Qdrant + Postgres + api; the bridge runs on the host with a
  Windows-specific Proactor event-loop launcher (`scripts/run_bridge.py`).

---

## Quickstart

```bash
# host: install uv + pull the bridge binaries
uv sync
docker compose up -d qdrant postgres
docker compose build api && docker compose up -d api

# host: launch the CLI bridge (claude-cli + gemini-cli must already be logged in,
# Ollama must be running, qwen3:8b-q8_0 must be pulled)
uv run python scripts/run_bridge.py

# frontend
cd web && npm install && npm run dev
```

Then visit <http://localhost:3000>. Set provider config in Settings (Ingest disambiguation defaults
to ollama qwen3; you can switch it to claude-cli/sonnet for sharper questions on visual files).

---

## Layout

```
api/             FastAPI routes (ingest, chat, query, files, clarifications, ...)
core/            pipeline, buckets, prompts, retag, clarification + chat-job stores
providers/       cli (claude, gemini), http_bridge, embeddings, vision
profiling/       modality + structure profiler
ingestion/       per-modality preprocessors
chunking/        code-AST, paper-section, naive
enrichment/      contextual, metadata, ambiguity (each takes an optional @<path> attachment)
index/           qdrant hybrid (fetch_doc, distinct_entities, search)
retrieval/       hybrid retriever, query rewrite
rerank/          cross-encoder
tuning/          Optuna study runner
scripts/         cli_bridge, run_bridge, permission_mcp (dormant)
web/             Next.js frontend (chat, ingest, files, search, optimizer, settings)
```

---

## Status

Built incrementally over ~14 rounds. Currently runs end-to-end for single-user multimodal RAG with
clarifications, agent visibility (claude + gemini), per-chat scope, chat resume across refresh /
container restart / mid-stream crash, and a working optimizer. The remaining roadmap items are
real pre-approval permission gating (needs an SDK rewrite of agent mode) and a few smaller
quality-of-life ones (vision-capable enricher selectable in Settings the same way ambiguity is).
