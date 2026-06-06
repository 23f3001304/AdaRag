"""Route endpoints: classify a chat message's intent.

/route - ingest-vs-ask for an attachment-bearing message (used when a file is attached).
/route/skill - ask-vs-skill for a plain message that a client heuristic already flagged as
plausibly a skill-creation request, so the LLM only sees those few candidates.
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


@router.post("/route/skill")
async def route_skill(request: Request, body: RouteRequest) -> dict:
    """Confirm that a heuristic-flagged message is genuinely a skill-creation request."""
    is_skill = await request.app.state.skill_router.is_skill(body.message)
    return {"intent": "skill" if is_skill else "ask"}
