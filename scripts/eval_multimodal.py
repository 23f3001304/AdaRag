"""Cross-modal coverage + cost benchmark (Phase 4): ingest text/image/audio/video, query each.

Shows a text query retrieving the right modality (Text -> Image/Audio/Video too), and reports the
cost per ingested MB + cost per query — the data the Phase 5 optimizer builds on. Local compute
(bge-m3 embeddings, whisper) is free; only the cloud LLM/vision calls carry a dollar cost.

Run: uv run python scripts/eval_multimodal.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from chunking.registry import build_chunker  # noqa: E402
from core.config import Settings  # noqa: E402
from core.db import Database  # noqa: E402
from core.pipeline import AnswerService, IngestService  # noqa: E402
from core.usage import METER  # noqa: E402
from evaluation.reset import reset_corpus  # noqa: E402
from index.qdrant_client import create_qdrant  # noqa: E402
from index.qdrant_hybrid import QdrantIndex  # noqa: E402
from ingestion.registry import build_registry  # noqa: E402
from providers.factory import ProviderFactory  # noqa: E402
from rerank.cross_encoder import CrossEncoderReranker  # noqa: E402
from retrieval.hybrid import HybridRetriever  # noqa: E402

TEXT_DOCS = ["profiling.txt", "chunking.txt", "embeddings.txt", "retrieval.txt", "evaluation.txt"]
MEDIA = ["data/mm_image.png", "data/mm_audio.wav", "data/mm_video.mp4"]
QUERIES = [
    ("text", "how does bge-m3 produce dense and sparse embeddings?"),
    ("image", "knowledge graph"),
    ("audio", "speaker diarization separating overlapping voices"),
    ("video", "scene detection segmenting video into shots and key frames"),
]


async def main() -> None:
    s = Settings()
    qdrant = create_qdrant(s.qdrant_url)
    db = Database(s.database_url)
    await db.create_all()
    index = QdrantIndex(qdrant, s.qdrant_collection)
    embedder = ProviderFactory(s).embeddings()
    llm = ProviderFactory(s).llm()
    vision = ProviderFactory(s).vision()
    chunker = build_chunker(s.chunk_size, s.chunk_overlap, s.adaptive_chunking)
    ingest = IngestService(chunker, embedder, index, db)
    registry = build_registry(vision)
    retriever = HybridRetriever(embedder, index, s.rerank_candidates)
    answer = AnswerService(retriever, CrossEncoderReranker(s.rerank_model), llm, s.top_k)

    await reset_corpus(qdrant, db, s.qdrant_collection)
    total_bytes = 0
    METER.reset()
    for name in TEXT_DOCS:
        p = ROOT / "evaluation" / "corpus" / name
        await ingest.ingest(name, p.read_text(encoding="utf-8"))
        total_bytes += p.stat().st_size
    for media in MEDIA:
        p = ROOT / media
        doc = await registry.preprocess(p)
        await ingest.ingest(doc.source, doc.text, doc.modality, doc.original_path)
        total_bytes += p.stat().st_size
    ingest_u = METER.snapshot()
    mb = total_bytes / 1e6

    print(f"\ningested {len(TEXT_DOCS)} text + {len(MEDIA)} media ({mb:.2f} MB)")
    print(f"ingest: {ingest_u.line()}  ->  ${ingest_u.cost_usd / mb:.4f} per MB\n")
    print(f"{'query':<7}   {'top modality':<13}{'source':<16}{'$/query':>9}{'s/query':>9}")

    q_cost = q_ms = 0.0
    for want, q in QUERIES:
        METER.reset()
        res = await answer.answer(q)
        u = METER.snapshot()
        q_cost += u.cost_usd
        q_ms += u.ms
        top = res["citations"][0] if res["citations"] else {}
        mod = top.get("modality", "-")
        mark = "OK" if mod == want else "x"
        cells = f"{want:<7}-> {mod:<11}{mark:<2} {top.get('source', '-'):<16}"
        print(f"{cells}{u.cost_usd:>9.4f}{u.ms / 1000:>9.1f}")
    n = len(QUERIES)
    print(f"\navg per query: ${q_cost / n:.4f}   {q_ms / n / 1000:.1f}s")
    await db.dispose()
    await qdrant.close()


if __name__ == "__main__":
    asyncio.run(main())
