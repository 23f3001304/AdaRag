"""FastAPI application: wiring, lifespan-managed services, and routes."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.buckets import router as buckets_router
from api.chat import router as chat_router
from api.documents import router as documents_router
from api.health import router as health_router
from api.ingest import router as ingest_router
from api.query import router as query_router
from core.buckets import BucketManager
from core.config import get_settings
from core.db import Database
from index.qdrant_client import create_qdrant
from ingestion.registry import build_registry
from providers.factory import ProviderFactory


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build shared providers + the bucket manager, ensure tables, dispose clients on shutdown."""
    settings = get_settings()
    providers = ProviderFactory(settings)
    db = Database(settings.database_url)
    qdrant = create_qdrant(settings.qdrant_url)
    # The registry preprocesses uploads (image -> caption+OCR, audio/video -> text) before ingest.
    registry = build_registry(providers.vision(), settings.ocr_provider)

    await db.create_all()
    app.state.db = db
    app.state.qdrant = qdrant
    app.state.registry = registry
    app.state.buckets = BucketManager(qdrant, db, settings, providers)
    try:
        yield
    finally:
        await db.dispose()
        await qdrant.close()


app = FastAPI(title="AdaRag", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(query_router)
app.include_router(chat_router)
app.include_router(buckets_router)
app.include_router(documents_router)


@app.get("/")
async def root() -> dict:
    """Minimal landing payload."""
    return {"name": "AdaRag", "status": "up"}
