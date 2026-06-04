"""FastAPI application: wiring, lifespan-managed clients, and routes."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.health import router as health_router
from core.config import get_settings
from core.db import create_engine
from index.qdrant_client import create_qdrant


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open shared clients on startup, dispose them on shutdown."""
    settings = get_settings()
    app.state.db_engine = create_engine(settings.database_url)
    app.state.qdrant = create_qdrant(settings.qdrant_url)
    try:
        yield
    finally:
        await app.state.db_engine.dispose()
        await app.state.qdrant.close()


app = FastAPI(title="AdaRag", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)


@app.get("/")
async def root() -> dict:
    """Minimal landing payload."""
    return {"name": "AdaRag", "status": "up"}
