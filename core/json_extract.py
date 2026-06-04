"""Tolerant extraction of a JSON object from an LLM reply (handles surrounding prose/markdown)."""

from __future__ import annotations

import json
import re


def extract_json(raw: str) -> dict:
    """Pull the first {...} object out of an LLM reply (tolerates surrounding prose/markdown)."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
