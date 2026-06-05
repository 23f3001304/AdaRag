"""Query endpoint: retrieve relevant chunks and generate a cited answer."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from api.schemas import ModeOverride, SkillOverride

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    query: str
    bucket: str = "default"
    skill: SkillOverride | None = None
    mode: ModeOverride | None = None


@router.post("/query")
async def query(request: Request, body: QueryRequest) -> dict:
    """Answer a question over a bucket's corpus, with citations to source chunks."""
    buckets = request.app.state.buckets
    answer = buckets.services(body.bucket).answer
    skill = body.skill
    llm = buckets.llm_for(body.mode.provider, body.mode.model) if body.mode else None
    return await answer.answer(
        body.query,
        persona=skill.persona if skill else None,
        top_k=skill.top_k if skill else None,
        llm=llm,
    )
