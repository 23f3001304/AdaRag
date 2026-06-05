"""Chat endpoint: multi-turn RAG conversation with citations, keyed by session_id."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> dict:
    """Answer one conversational turn, contextualizing it against the session's history."""
    return await request.app.state.chat.chat(body.session_id, body.message)
