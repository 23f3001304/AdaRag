"""Query endpoint: retrieve relevant chunks and generate a cited answer."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from api.schemas import SkillOverride

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    query: str
    bucket: str = "default"
    skill: SkillOverride | None = None


@router.post("/query")
async def query(request: Request, body: QueryRequest) -> dict:
    """Answer a question over a bucket's corpus, with citations to source chunks."""
    answer = request.app.state.buckets.services(body.bucket).answer
    skill = body.skill
    return await answer.answer(
        body.query,
        persona=skill.persona if skill else None,
        top_k=skill.top_k if skill else None,
    )
