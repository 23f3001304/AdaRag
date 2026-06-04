"""Ingest endpoint: accept a text file and run it through the ingestion service."""

from __future__ import annotations

from fastapi import APIRouter, File, Request, UploadFile

router = APIRouter(tags=["ingest"])


@router.post("/ingest")
async def ingest(request: Request, file: UploadFile = File(...)) -> dict:
    """Ingest one UTF-8 text file: chunk -> embed -> store in Qdrant + Postgres."""
    text = (await file.read()).decode("utf-8", errors="replace")
    return await request.app.state.ingest.ingest(file.filename or "upload.txt", text)
