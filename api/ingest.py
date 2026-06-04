"""Ingest endpoint: accept a text file and run it through the ingestion pipeline."""

from __future__ import annotations

from fastapi import APIRouter, File, Request, UploadFile

from core.config import get_settings
from core.pipeline import ingest_text

router = APIRouter(tags=["ingest"])


@router.post("/ingest")
async def ingest(request: Request, file: UploadFile = File(...)) -> dict:
    """Ingest one UTF-8 text file: chunk -> embed -> store in Qdrant + Postgres."""
    text = (await file.read()).decode("utf-8", errors="replace")
    state = request.app.state
    return await ingest_text(
        source=file.filename or "upload.txt",
        text=text,
        settings=get_settings(),
        embedder=state.embedder,
        qdrant=state.qdrant,
        engine=state.db_engine,
    )
