"""Chat endpoint: multi-turn RAG conversation with citations, keyed by session_id."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str
    bucket: str = "default"


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> dict:
    """Answer one conversational turn in a bucket, contextualized against the session's history."""
    chat_service = request.app.state.buckets.services(body.bucket).chat
    return await chat_service.chat(body.session_id, body.message)
