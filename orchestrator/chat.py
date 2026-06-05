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

_CHITCHAT_PROMPT = """You are AdaRag, an assistant grounded in a private knowledge base. Reply
briefly and warmly to this greeting or small talk (1-2 sentences), then invite a question about the
user's documents. Do not invent facts.

User: {message}

Reply:"""

# Obvious greetings / small talk that should answer directly instead of triggering a retrieval.
_GREETINGS = frozenset(
    {
        "hi", "hello", "hey", "yo", "hiya", "howdy", "sup", "hi there", "hello there",
        "thanks", "thank you", "thx", "ty", "ok", "okay", "cool", "nice", "great", "awesome",
        "bye", "goodbye", "see you", "cya", "good night",
        "who are you", "what are you", "what can you do", "what do you do", "help",
        "how are you", "hows it going", "how's it going", "good morning", "good evening",
        "good afternoon",
    }
)


def _is_chitchat(message: str) -> bool:
    """Cheap, no-LLM check: an obvious greeting / small talk that shouldn't hit retrieval."""
    return message.strip().lower().rstrip("!.?") in _GREETINGS


async def _stream_or_full(llm, prompt: str):
    """Yield {type: text, ...} events from a streaming LLM, or one text event if it can't stream."""
    if hasattr(llm, "stream"):
        async for event in llm.stream(prompt):
            yield event
    else:
        yield {"type": "text", "text": (await llm.generate(prompt)).strip()}


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
        llm: LLMProvider | None = None,
        thinking: bool = False,
    ) -> dict:
        """Answer one turn in a session; rewrites follow-ups to standalone queries first.

        A skill may pass a ``persona`` and ``top_k``; a mode may pass an ``llm``; ``thinking`` adds
        the model's reasoning. A greeting answers directly (no retrieval, citations, or thinking).
        """
        gen = llm or self._llm
        history = self._sessions[session_id]
        if _is_chitchat(message):
            reply = (await gen.generate(_CHITCHAT_PROMPT.format(message=message))).strip()
            history.append((message, reply))
            return {"answer": reply, "citations": [], "search_query": None, "thinking": None}
        query = await self._contextualize(message, history, gen) if history else message
        result = await self._answer.answer(
            query, persona=persona, top_k=top_k, llm=llm, thinking=thinking
        )
        history.append((message, result["answer"]))
        return {
            "answer": result["answer"],
            "citations": result["citations"],
            "search_query": query,  # surfaced so the rewrite is inspectable
            "thinking": result.get("thinking"),
        }

    async def chat_stream(
        self,
        session_id: str,
        message: str,
        *,
        persona: str | None = None,
        top_k: int | None = None,
        llm: LLMProvider | None = None,
    ):
        """Stream a turn as events: {type: query|text|thinking|done}; history updated at the end."""
        gen = llm or self._llm
        history = self._sessions[session_id]
        if _is_chitchat(message):
            full = ""
            async for event in _stream_or_full(gen, _CHITCHAT_PROMPT.format(message=message)):
                if event.get("type") == "text":
                    full += event["text"]
                yield event
            history.append((message, full.strip()))
            yield {"type": "done", "citations": [], "search_query": None}
            return
        query = await self._contextualize(message, history, gen) if history else message
        yield {"type": "query", "text": query}
        full = ""
        async for event in self._answer.answer_stream(query, persona=persona, top_k=top_k, llm=llm):
            if event.get("type") == "done":
                yield {"type": "done", "citations": event["citations"], "search_query": query}
            else:
                if event.get("type") == "text":
                    full += event["text"]
                yield event
        history.append((message, full.strip()))

    async def _contextualize(
        self, message: str, history: deque[tuple[str, str]], llm: LLMProvider
    ) -> str:
        """Rewrite a follow-up into a standalone query from history (else the message)."""
        convo = "\n".join(f"User: {user}\nAssistant: {ans}" for user, ans in history)
        prompt = _CONTEXTUALIZE_PROMPT.format(history=convo, message=message)
        rewritten = (await llm.generate(prompt)).strip()
        return rewritten or message
