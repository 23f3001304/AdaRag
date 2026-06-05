"""Shared request models for optional per-request skill overrides on /query and /chat."""

from __future__ import annotations

from pydantic import BaseModel


class SkillOverride(BaseModel):
    """Answer-time overrides carried by a frontend skill: a persona and a retrieval depth.

    Both are optional; an absent field leaves the bucket's configured default in place.
    """

    persona: str | None = None
    top_k: int | None = None
