"""Eval dataset: generate question-answer pairs from chunks (seeds the golden eval set)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from core.interfaces import LLMProvider


@dataclass(frozen=True)
class QAPair:
    """A question, its grounded answer, and the chunk it came from (the relevant doc for recall)."""

    question: str
    answer: str
    chunk_id: str
    source: str


_GEN_PROMPT = """From the passage, write one specific question answerable ONLY from it, plus a \
concise answer. Reply as JSON: {{"question": "...", "answer": "..."}} and nothing else.

Passage:
{text}"""


def _extract_json(raw: str) -> dict:
    """Pull the first {...} object out of an LLM reply (tolerates surrounding prose/markdown)."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


class QAGenerator:
    """Uses an LLM to generate one QA pair per chunk — the seed of the golden eval set."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def from_chunk(self, chunk_id: str, source: str, text: str) -> QAPair | None:
        """Generate one QA pair grounded in a chunk; returns None if the reply is unusable."""
        data = _extract_json(await self._llm.generate(_GEN_PROMPT.format(text=text)))
        if not data.get("question") or not data.get("answer"):
            return None
        return QAPair(str(data["question"]), str(data["answer"]), chunk_id, source)
