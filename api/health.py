"""Health endpoint: reports liveness of the API and its backing services."""

from __future__ import annotations

from fastapi import APIRouter, Request

from core.db import ping_db
from index.qdrant_client import ping_qdrant

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict:
    """Ping Postgres and Qdrant; status is 'ok' only when both answer."""
    state = request.app.state
    services = {
        "postgres": await ping_db(state.db_engine),
        "qdrant": await ping_qdrant(state.qdrant),
    }
    return {"status": "ok" if all(services.values()) else "degraded", "services": services}
