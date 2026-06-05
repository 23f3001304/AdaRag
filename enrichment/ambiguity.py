"""Ingest-time entity disambiguation: judge whether a file's subject is identifiable.

A photo captioned "a young man ..." or a file that never names its subject can't be linked to a
person, so two people's photos become indistinguishable. The detector asks the LLM to make that
call per file; an ambiguous verdict raises a clarifying question for the user to answer.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.interfaces import LLMProvider
from core.json_extract import extract_json

_PROMPT = """A file was added to a knowledge base. Decide if it is clear which single named subject
(a specific person, product, project, or place) the file is primarily about, or if that is
ambiguous and a human should say who or what it is.

Ambiguous: a photo described only as "a young man"; text that never names its subject.
Clear: a resume that states the person's name; an invoice that names the company.

Reply with JSON only:
{{"ambiguous": true | false,
  "subject": "<short noun phrase for the unnamed subject, e.g. 'the person in this photo'>",
  "question": "<one short question for the user, e.g. 'Who is the person in this image?'>"}}

Modality: {modality}
Content:
{text}"""


@dataclass(frozen=True)
class Ambiguity:
    """A file whose subject the LLM couldn't pin down, with a question to put to the user."""

    subject: str
    question: str


class AmbiguityDetector:
    """One LLM call per file: is its subject identifiable, or should we ask the user who it is?"""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def detect(self, text: str, modality: str) -> Ambiguity | None:
        """Return an Ambiguity to clarify, or None when the subject is already identifiable."""
        raw = await self._llm.generate(_PROMPT.format(modality=modality, text=text[:2000]))
        data = extract_json(raw)
        if not data.get("ambiguous"):
            return None
        question = str(data.get("question") or "").strip()
        if not question:
            return None
        return Ambiguity(subject=str(data.get("subject") or "").strip(), question=question)
