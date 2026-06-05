"""Models endpoint: the provider+model combos available for chat model switching."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["models"])


@router.get("/models")
async def models(request: Request) -> dict:
    """List the provider+model 'modes' available to switch between (detected on the host)."""
    return {"modes": await request.app.state.buckets.available_modes()}
