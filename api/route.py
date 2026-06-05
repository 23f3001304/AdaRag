"""Route endpoint: classify an attachment-bearing chat message as 'ingest' or 'ask'.

The chat UI calls this when a file is attached, then either ingests the file or asks normally.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["route"])


class RouteRequest(BaseModel):
    message: str


@router.post("/route")
async def route(request: Request, body: RouteRequest) -> dict:
    """Classify the intent of a chat message that has a document attached."""
    is_ingest = await request.app.state.router.is_ingest(body.message)
    return {"intent": "ingest" if is_ingest else "ask"}
