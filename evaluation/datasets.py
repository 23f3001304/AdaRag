"""Eval dataset: generate question-answer pairs from chunks (seeds the golden eval set)."""

from __future__ import annotations

from dataclasses import dataclass

from core.interfaces import LLMProvider
from core.json_extract import extract_json


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

_HARD_GEN_PROMPT = """You are given a document and one chunk from it.

<document>
{document}
</document>

<chunk>
{chunk}
</chunk>

Write a search query a user would type to find the information in the chunk. The user knows the \
document's topic but has not seen this chunk, so name the subject explicitly using the document's \
terminology, and do NOT copy distinctive wording from the chunk. Also give a short answer drawn \
from the chunk. Reply as JSON: {{"question": "...", "answer": "..."}} and nothing else."""

_TERM_GEN_PROMPT = """\
Write a short search query that hinges on a specific named thing in the passage — a product,
technology, tool, or proper noun someone would recall and search by. Include that term, and
give a short answer from the passage. Reply as JSON only: {{"question": "...", "answer": "..."}}.

Passage:
{text}"""

_SPAN_GEN_PROMPT = """\
From the passage, write a question, and copy the single exact sentence (verbatim, word-for-word)
from the passage that answers it. Reply as JSON only:
{{"question": "...", "answer": "<exact sentence copied from the passage>"}}.

Passage:
{text}"""


class QAGenerator:
    """Uses an LLM to generate one QA pair per chunk — the seed of the golden eval set."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def from_chunk(self, chunk_id: str, source: str, text: str) -> QAPair | None:
        """Generate one QA pair grounded in a chunk; returns None if the reply is unusable."""
        data = extract_json(await self._llm.generate(_GEN_PROMPT.format(text=text)))
        if not data.get("question") or not data.get("answer"):
            return None
        return QAPair(str(data["question"]), str(data["answer"]), chunk_id, source)

    async def hard_from_chunk(
        self, chunk_id: str, source: str, document: str, text: str
    ) -> QAPair | None:
        """Generate a realistic query that names the subject but does not quote the chunk.

        This is the query shape contextual enrichment is meant to help: an ambiguous chunk
        (pronouns, "this approach") matches a topic-named query only once it carries a situating
        context. Returns None if the reply is unusable.
        """
        prompt = _HARD_GEN_PROMPT.format(document=document[:6000], chunk=text)
        data = extract_json(await self._llm.generate(prompt))
        if not data.get("question") or not data.get("answer"):
            return None
        return QAPair(str(data["question"]), str(data["answer"]), chunk_id, source)

    async def term_from_chunk(self, chunk_id: str, source: str, text: str) -> QAPair | None:
        """Generate a query hinging on a specific named term in the chunk (the exact-match case)."""
        data = extract_json(await self._llm.generate(_TERM_GEN_PROMPT.format(text=text)))
        if not data.get("question") or not data.get("answer"):
            return None
        return QAPair(str(data["question"]), str(data["answer"]), chunk_id, source)

    async def span_from_chunk(self, chunk_id: str, source: str, text: str) -> QAPair | None:
        """Generate a question + a VERBATIM answer span copied from the chunk.

        The span is real corpus text, so it can be found in whichever chunk covers it regardless of
        how the document was split — the gold for comparing chunking strategies.
        """
        data = extract_json(await self._llm.generate(_SPAN_GEN_PROMPT.format(text=text)))
        if not data.get("question") or not data.get("answer"):
            return None
        return QAPair(str(data["question"]), str(data["answer"]), chunk_id, source)
