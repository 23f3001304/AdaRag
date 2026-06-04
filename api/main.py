"""FastAPI application: wiring, lifespan-managed services, and routes."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.health import router as health_router
from api.ingest import router as ingest_router
from api.query import router as query_router
from chunking.registry import build_chunker
from core.config import get_settings
from core.db import Database
from core.pipeline import AnswerService, IngestService
from enrichment.contextual import ContextualEnricher
from enrichment.metadata import MetadataEnricher
from index.qdrant_client import create_qdrant
from index.qdrant_hybrid import QdrantIndex
from providers.factory import ProviderFactory
from rerank.cross_encoder import CrossEncoderReranker
from retrieval.hybrid import HybridRetriever


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the services from config, ensure tables, and dispose clients on shutdown."""
    settings = get_settings()
    providers = ProviderFactory(settings)
    embedder = providers.embeddings()
    db = Database(settings.database_url)
    qdrant = create_qdrant(settings.qdrant_url)
    index = QdrantIndex(qdrant, settings.qdrant_collection)
    chunker = build_chunker(settings.chunk_size, settings.chunk_overlap, settings.adaptive_chunking)
    retriever = HybridRetriever(embedder, index, settings.rerank_candidates)
    reranker = CrossEncoderReranker(settings.rerank_model)
    llm = providers.llm()
    enricher = ContextualEnricher(llm) if settings.enrich_context else None
    metadata = MetadataEnricher(llm) if settings.enrich_metadata else None

    await db.create_all()
    app.state.db = db
    app.state.qdrant = qdrant
    app.state.ingest = IngestService(chunker, embedder, index, db, enricher, metadata)
    app.state.answer = AnswerService(retriever, reranker, llm, settings.top_k)
    try:
        yield
    finally:
        await db.dispose()
        await qdrant.close()


app = FastAPI(title="AdaRag", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(query_router)


@app.get("/")
async def root() -> dict:
    """Minimal landing payload."""
    return {"name": "AdaRag", "status": "up"}
