"""Query rewriting: expand a user query into a fuller search query for better recall (DESIGN.md)."""

from __future__ import annotations

from core.interfaces import LLMProvider

_REWRITE_PROMPT = """\
Rewrite this search query to improve retrieval: expand it with key synonyms, full terms, and the
related concepts a relevant passage would use. Keep it to one line; reply with only the query.

Query: {query}"""


class QueryRewriter:
    """Uses an LLM to expand a query with synonyms / related terms before retrieval."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def rewrite(self, query: str) -> str:
        """Return an expanded search query (falls back to the original on an empty reply)."""
        rewritten = (await self._llm.generate(_REWRITE_PROMPT.format(query=query))).strip()
        return rewritten or query
