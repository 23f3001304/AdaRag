"""Skills endpoint: draft a skill spec from a description (the /skill-creator flow)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from core.json_extract import extract_json

router = APIRouter(tags=["skills"])

_DRAFT_PROMPT = """Turn this description of an assistant into a reusable skill spec for a RAG chat.
Reply as JSON only, nothing else:
{{"name": "<3-4 words>", "persona": "<system prompt, 1-2 sentences>", "top_k": <3-10>}}

Description: {description}"""


class DraftRequest(BaseModel):
    description: str


@router.post("/skills/draft")
async def draft(request: Request, body: DraftRequest) -> dict:
    """Use the LLM to turn a description into a {name, persona, top_k} skill the user can save."""
    raw = await request.app.state.buckets.llm.generate(
        _DRAFT_PROMPT.format(description=body.description)
    )
    data = extract_json(raw)
    top_k = data.get("top_k")
    return {
        "name": str(data.get("name") or "New skill")[:48],
        "persona": str(data.get("persona") or ""),
        "top_k": int(top_k) if isinstance(top_k, int) and 1 <= top_k <= 20 else 5,
    }
