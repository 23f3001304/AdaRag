"""FastAPI application: wiring, lifespan-managed services, and routes."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.buckets import router as buckets_router
from api.chat import router as chat_router
from api.documents import router as documents_router
from api.files import router as files_router
from api.health import router as health_router
from api.ingest import router as ingest_router
from api.models import router as models_router
from api.optimize import router as optimize_router
from api.query import router as query_router
from api.route import router as route_router
from core.buckets import BucketManager
from core.config import get_settings
from core.db import Database
from index.qdrant_client import create_qdrant
from ingestion.registry import build_registry
from orchestrator.router import IntentRouter
from providers.factory import ProviderFactory
from tuning.study import StudyRunner


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
    buckets = BucketManager(qdrant, db, settings, providers)
    app.state.buckets = buckets
    app.state.router = IntentRouter(buckets.llm)  # bucket-independent chat intent classifier
    app.state.study = StudyRunner(buckets, qdrant, settings)  # frontend-triggered tuning study
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
app.include_router(route_router)
app.include_router(buckets_router)
app.include_router(documents_router)
app.include_router(files_router)
app.include_router(optimize_router)
app.include_router(models_router)


@app.get("/")
async def root() -> dict:
    """Minimal landing payload."""
    return {"name": "AdaRag", "status": "up"}
