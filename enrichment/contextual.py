"""Contextual enrichment: a short LLM-written context prepended to each chunk (recall lift)."""

from __future__ import annotations

from core.interfaces import LLMProvider

_PROMPT = """<document>
{document}
</document>

Here is a chunk from that document:
<chunk>
{chunk}
</chunk>

Write a short (1-2 sentence) context that situates this chunk within the document, to improve \
search retrieval. Reply with the context only, nothing else."""


class ContextualEnricher:
    """Writes a situating context for a chunk (Anthropic-style contextual retrieval)."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def context_for(self, chunk: str, document: str) -> str:
        """Return a 1-2 sentence context that situates the chunk within its document."""
        prompt = _PROMPT.format(document=document[:8000], chunk=chunk)
        return (await self._llm.generate(prompt)).strip()
