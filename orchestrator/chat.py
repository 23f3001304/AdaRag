"""Conversational orchestration: multi-turn RAG chat over the answer pipeline.

The key move is *query contextualization*: a follow-up ("what about its limits?") is rewritten into
a standalone query using recent turns, so retrieval sees a self-contained question. The answer is
then grounded in freshly retrieved context (history shapes the query, not the answer) and returned
with citations. Sessions live in memory, keyed by id, with bounded history.
"""

from __future__ import annotations

from collections import defaultdict, deque

from core.interfaces import LLMProvider
from core.pipeline import AnswerService

_CONTEXTUALIZE_PROMPT = """Given the conversation and a follow-up message, rewrite the follow-up
as a standalone search query that stands on its own (resolve pronouns and references). Reply with
ONLY the rewritten query, no preamble or quotes.

Conversation:
{history}

Follow-up: {message}

Standalone query:"""


class ChatOrchestrator:
    """Multi-turn RAG chat: contextualize each turn against history, then answer with citations."""

    def __init__(self, answer: AnswerService, llm: LLMProvider, max_turns: int = 6) -> None:
        self._answer = answer
        self._llm = llm
        self._sessions: dict[str, deque[tuple[str, str]]] = defaultdict(
            lambda: deque(maxlen=max_turns)
        )

    async def chat(
        self,
        session_id: str,
        message: str,
        *,
        persona: str | None = None,
        top_k: int | None = None,
    ) -> dict:
        """Answer one turn in a session; rewrites follow-ups to standalone queries first.

        An applied skill may pass a ``persona`` (system framing) and ``top_k`` (retrieval depth).
        """
        history = self._sessions[session_id]
        query = await self._contextualize(message, history) if history else message
        result = await self._answer.answer(query, persona=persona, top_k=top_k)
        history.append((message, result["answer"]))
        return {
            "answer": result["answer"],
            "citations": result["citations"],
            "search_query": query,  # surfaced so the rewrite is inspectable
        }

    async def _contextualize(self, message: str, history: deque[tuple[str, str]]) -> str:
        """Rewrite a follow-up into a standalone query from history (else the message)."""
        convo = "\n".join(f"User: {user}\nAssistant: {ans}" for user, ans in history)
        prompt = _CONTEXTUALIZE_PROMPT.format(history=convo, message=message)
        rewritten = (await self._llm.generate(prompt)).strip()
        return rewritten or message
