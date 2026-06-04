"""FastAPI application: wiring, lifespan-managed clients, and routes."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.health import router as health_router
from api.ingest import router as ingest_router
from api.query import router as query_router
from core.config import get_settings
from core.db import create_engine
from core.models import create_all
from index.qdrant_client import create_qdrant
from providers.factory import build_embeddings, build_llm


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open shared clients + ensure tables on startup; dispose on shutdown."""
    settings = get_settings()
    app.state.db_engine = create_engine(settings.database_url)
    app.state.qdrant = create_qdrant(settings.qdrant_url)
    app.state.embedder = build_embeddings(settings)
    app.state.llm = build_llm(settings)
    await create_all(app.state.db_engine)
    try:
        yield
    finally:
        await app.state.db_engine.dispose()
        await app.state.qdrant.close()


app = FastAPI(title="AdaRag", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(query_router)


@app.get("/")
async def root() -> dict:
    """Minimal landing payload."""
    return {"name": "AdaRag", "status": "up"}
