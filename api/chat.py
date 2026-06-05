"""Chat endpoint: multi-turn RAG conversation with citations, keyed by session_id."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.schemas import ModeOverride, SkillOverride

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str
    bucket: str = "default"
    skill: SkillOverride | None = None
    mode: ModeOverride | None = None
    thinking: bool = False


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> dict:
    """Answer one conversational turn in a bucket, contextualized against the session's history."""
    buckets = request.app.state.buckets
    chat_service = buckets.services(body.bucket).chat
    skill = body.skill
    llm = buckets.llm_for(body.mode.provider, body.mode.model) if body.mode else None
    return await chat_service.chat(
        body.session_id,
        body.message,
        persona=skill.persona if skill else None,
        top_k=skill.top_k if skill else None,
        llm=llm,
        thinking=body.thinking,
    )


@router.post("/chat/stream")
async def chat_stream(request: Request, body: ChatRequest) -> StreamingResponse:
    """Stream a chat turn as SSE: `data: {type: query|text|thinking|done|error, ...}` per line."""
    buckets = request.app.state.buckets
    chat_service = buckets.services(body.bucket).chat
    skill = body.skill
    llm = buckets.llm_for(body.mode.provider, body.mode.model) if body.mode else None

    async def events():
        try:
            async for ev in chat_service.chat_stream(
                body.session_id,
                body.message,
                persona=skill.persona if skill else None,
                top_k=skill.top_k if skill else None,
                llm=llm,
            ):
                yield f"data: {json.dumps(ev)}\n\n"
        except Exception as exc:  # surface failures to the client instead of a dropped stream
            yield f"data: {json.dumps({'type': 'error', 'text': str(exc)})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
