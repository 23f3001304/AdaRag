"""Query transforms: rewrite/expand or HyDE, to improve retrieval (DESIGN.md query layer)."""

from __future__ import annotations

from typing import Protocol

from core.interfaces import LLMProvider

_REWRITE_PROMPT = """\
Rewrite this search query to improve retrieval: expand it with key synonyms, full terms, and the
related concepts a relevant passage would use. Use natural language only — no boolean operators
(no AND/OR). Keep it to one line; reply with only the rewritten query.

Query: {query}"""

_HYDE_PROMPT = """\
Write a short, factual passage (2-3 sentences) that directly answers the question below, as if it
were an excerpt from a technical document. It need not be correct in every detail — it is only a
retrieval probe. Reply with only the passage.

Question: {query}"""


class QueryTransformer(Protocol):
    """Transforms a user query into the text used for retrieval (rewrite, HyDE, ...)."""

    async def transform(self, query: str) -> str: ...


class QueryRewriter:
    """Expands a query with synonyms / related terms before retrieval (better recall)."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def transform(self, query: str) -> str:
        out = (await self._llm.generate(_REWRITE_PROMPT.format(query=query))).strip()
        return out or query


class HydeTransformer:
    """HyDE: generate a hypothetical answer and retrieve with the query plus that answer, which sits
    nearer real passages in embedding space than the bare question."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def transform(self, query: str) -> str:
        out = (await self._llm.generate(_HYDE_PROMPT.format(query=query))).strip()
        return f"{query}\n\n{out}" if out else query
