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

_SKILL_PROMPT = """A user typed this into chat. Decide if they are asking to CREATE a custom
assistant / skill / persona (something they want built and reused), or just asking a question.

- "skill" if they want a new assistant, persona, skill, expert, analyst, reviewer, etc. built.
  Examples: "make me a terse security analyst that cites sources",
            "build a skill that always answers in bullet points".
- "ask" if they are asking a question, requesting an analysis, or anything else.

Reply with ONLY one word: skill or ask.

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


class SkillIntentRouter:
    """One cheap LLM call that confirms a heuristic-flagged skill-creation message.

    The frontend runs a fast client-side heuristic first; this LLM check only runs when that
    heuristic flags a message as plausibly a skill request, so normal questions add zero latency.
    """

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def is_skill(self, message: str) -> bool:
        """True when the user wants a new skill/assistant created (False on doubt)."""
        verdict = (await self._llm.generate(_SKILL_PROMPT.format(message=message))).strip().lower()
        return verdict.startswith("skill")
