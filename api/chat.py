"""Chat endpoint: multi-turn RAG conversation with citations, keyed by session_id.

Streaming answers run as background jobs (api/chat_jobs.py) so a refresh or closed tab never loses
one: the tab reconnects via GET /chat/stream/{message_id}, and Stop hits POST /chat/stop/{id}.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.schemas import ModeOverride, SkillOverride

router = APIRouter(tags=["chat"])

# no-transform stops the dev proxy gzip-buffering the stream into one burst.
_SSE_HEADERS = {"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"}


class ChatRequest(BaseModel):
    session_id: str
    message: str
    message_id: str = ""  # client id so a reconnecting tab can resume this exact answer
    bucket: str = "default"
    skill: SkillOverride | None = None
    mode: ModeOverride | None = None
    thinking: bool = False
    agent: bool = False  # per-chat agent mode flag; slice 2B wires --permission-prompt-tool
    scope: str = "strict"  # answer scope: strict (context only) | medium (+general) | lazy (open)


def _sse(events: AsyncIterator[dict]) -> StreamingResponse:
    async def body() -> AsyncIterator[str]:
        async for ev in events:
            yield f"data: {json.dumps(ev)}\n\n"

    return StreamingResponse(body(), media_type="text/event-stream", headers=_SSE_HEADERS)


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> dict:
    """Answer one conversational turn in a bucket, contextualized against the session's history."""
    buckets = request.app.state.buckets
    chat_service = buckets.services(body.bucket).chat
    skill = body.skill
    llm = (
        buckets.llm_for(body.mode.provider, body.mode.model, body.agent) if body.mode else None
    )
    return await chat_service.chat(
        body.session_id,
        body.message,
        persona=skill.persona if skill else None,
        top_k=skill.top_k if skill else None,
        llm=llm,
        thinking=body.thinking,
        scope=body.scope,
    )


@router.post("/chat/stream")
async def chat_stream(request: Request, body: ChatRequest) -> StreamingResponse:
    """Start an answer job and stream it; the job keeps generating if the client disconnects."""
    buckets = request.app.state.buckets
    chat_service = buckets.services(body.bucket).chat
    skill = body.skill
    llm = (
        buckets.llm_for(body.mode.provider, body.mode.model, body.agent) if body.mode else None
    )
    gen = chat_service.chat_stream(
        body.session_id,
        body.message,
        persona=skill.persona if skill else None,
        top_k=skill.top_k if skill else None,
        llm=llm,
        scope=body.scope,
    )
    job = request.app.state.chat_jobs.start(body.message_id, gen)
    return _sse(job.observe())


@router.get("/chat/stream/{message_id}")
async def resume_stream(request: Request, message_id: str) -> StreamingResponse:
    """Reconnect a tab to an in-flight or just-finished answer (replays, then streams the rest)."""
    job = await request.app.state.chat_jobs.get(message_id)
    if job is None:

        async def gone() -> AsyncIterator[dict]:
            yield {"type": "gone"}  # the job expired or the server restarted

        return _sse(gone())
    return _sse(job.observe())


@router.post("/chat/stop/{message_id}")
async def stop_stream(request: Request, message_id: str) -> dict:
    """Explicitly stop generation - a dropped connection no longer cancels it on its own."""
    return {"stopped": request.app.state.chat_jobs.stop(message_id)}
