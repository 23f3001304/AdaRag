"""Ingest-time disambiguation: ask the model what a file leaves unclear.

A photo captioned "a man on a bike" is findable by almost nothing useful - not the rider, the
brand, or the race. The detector asks the LLM, in one call, which questions a person should answer
to make the file retrievable, with candidate answers drawn from the bucket's known entities. Each
question becomes a clarification the user answers on the Ingest tab.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.interfaces import LLMProvider
from core.json_extract import extract_json

_PROMPT = """A file was added to a knowledge base. List only the questions a person must still
answer to make it findable - who or what it shows, and key context - that the content does NOT
already state. For a race photo that names nobody: the rider, the bike brand, the event, who won.
Skip anything the content already states. Draw candidate answers from the known entities.

Known entities in the knowledge base: {entities}

Reply with JSON only. Ask 0 to 4 questions; ask none if the content already states what it shows:
{{"questions": [{{"question": "<short>", "candidates": [<entities that may answer it>]}}]}}

Modality: {modality}
Content:
{text}"""


@dataclass(frozen=True)
class Question:
    """One thing the model wants clarified, with candidate answers from the bucket's entities."""

    question: str
    candidates: list[str] = field(default_factory=list)


class AmbiguityDetector:
    """One LLM call per file: what should a person clarify to make this file findable?"""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def analyze(self, text: str, modality: str, entities: list[str]) -> list[Question]:
        """Questions to put to the user (empty when the file already states what's needed)."""
        prompt = _PROMPT.format(
            modality=modality, text=text[:2000], entities=", ".join(entities) or "(none yet)"
        )
        try:
            data = extract_json(await self._llm.generate(prompt))
        except Exception:
            return []
        raw = data.get("questions")
        if not isinstance(raw, list):
            return []
        known = set(entities)
        out: list[Question] = []
        for item in raw[:4]:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question") or "").strip()
            if not question:
                continue
            cands = [s for c in (item.get("candidates") or []) if (s := str(c).strip()) in known]
            out.append(Question(question=question, candidates=cands))
        return out
