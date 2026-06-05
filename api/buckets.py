"""Buckets endpoint: list, create, delete isolated RAG pipelines (one Qdrant collection each)."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["buckets"])


@router.get("/buckets")
async def list_buckets(request: Request) -> dict:
    """List every bucket that has a collection."""
    return {"buckets": await request.app.state.buckets.list_buckets()}


@router.post("/buckets/{name}")
async def create_bucket(request: Request, name: str) -> dict:
    """Pre-create a bucket's collection (ingesting into a new bucket also auto-creates it)."""
    return {"bucket": await request.app.state.buckets.create(name), "status": "created"}


@router.delete("/buckets/{name}")
async def delete_bucket(request: Request, name: str) -> dict:
    """Drop a bucket and all its data (the default bucket is protected)."""
    await request.app.state.buckets.delete(name)
    return {"bucket": name, "status": "deleted"}
