"""Documents endpoint: list the files indexed in a bucket (aggregated from its chunks)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

router = APIRouter(tags=["documents"])


@router.get("/documents")
async def list_documents(request: Request, bucket: str = "default") -> dict:
    """List the source files ingested into a bucket, each with its modality and chunk count."""
    return {"documents": await request.app.state.buckets.documents(bucket)}


@router.delete("/documents")
async def delete_document(
    request: Request, source: str = Query(...), bucket: str = "default"
) -> dict:
    """Delete one source file from a bucket (its chunks, Postgres rows, and preserved original)."""
    await request.app.state.buckets.delete_document(bucket, source)
    return {"bucket": bucket, "source": source, "status": "deleted"}
