"""Query endpoint: retrieve relevant chunks and generate a cited answer."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from core.config import get_settings
from core.pipeline import answer_query

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    query: str


@router.post("/query")
async def query(request: Request, body: QueryRequest) -> dict:
    """Answer a question over the ingested corpus, with citations to source chunks."""
    state = request.app.state
    return await answer_query(
        query=body.query,
        settings=get_settings(),
        embedder=state.embedder,
        llm=state.llm,
        qdrant=state.qdrant,
    )
