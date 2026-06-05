"""Intent routing: decide whether an attachment-bearing chat message means 'ingest' or 'ask'.

When a user attaches a document in chat, one cheap LLM call classifies their message so a request
like "ingest this" adds the file to the bucket, while "what does this say?" is answered normally.
"""

from __future__ import annotations

from core.interfaces import LLMProvider

_ROUTE_PROMPT = """A user attached a file in chat and sent this. Classify their intent:
- "ingest" if they want to add, save, ingest, index, upload, or remember the document.
- "ask" if they are asking a question or anything else.

Reply with ONLY one word: ingest or ask.

Message: {message}

Intent:"""


class IntentRouter:
    """One cheap LLM call that classifies an attachment-bearing message as 'ingest' or 'ask'."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def is_ingest(self, message: str) -> bool:
        """True when the user wants the attached document ingested (defaults to False on doubt)."""
        verdict = (await self._llm.generate(_ROUTE_PROMPT.format(message=message))).strip().lower()
        return verdict.startswith("ingest")
