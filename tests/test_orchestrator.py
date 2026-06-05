"""Unit tests for the ChatOrchestrator's multi-turn contextualization (fakes, no stack)."""

from __future__ import annotations

from orchestrator.chat import ChatOrchestrator


class _FakeAnswer:
    """Records the queries it was asked and echoes a cited answer."""

    def __init__(self) -> None:
        self.queries: list[str] = []

    async def answer(self, query: str) -> dict:
        self.queries.append(query)
        return {"answer": f"answer to '{query}'", "citations": [{"n": 1, "source": "doc.txt"}]}


class _FakeLLM:
    """Returns a fixed rewrite and counts how often it was called."""

    model = "fake"

    def __init__(self, rewrite: str = "rewritten query") -> None:
        self._rewrite = rewrite
        self.calls = 0

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        self.calls += 1
        return self._rewrite


async def test_first_turn_uses_message_directly():
    answer, llm = _FakeAnswer(), _FakeLLM()
    out = await ChatOrchestrator(answer, llm).chat("s1", "what is dense retrieval?")
    assert out["search_query"] == "what is dense retrieval?"
    assert answer.queries == ["what is dense retrieval?"]
    assert llm.calls == 0  # no contextualization on the first turn
    assert out["citations"]


async def test_followup_is_contextualized():
    answer, llm = _FakeAnswer(), _FakeLLM("limitations of dense retrieval")
    chat = ChatOrchestrator(answer, llm)
    await chat.chat("s1", "what is dense retrieval?")
    out = await chat.chat("s1", "what about its limits?")
    assert llm.calls == 1  # the follow-up was rewritten using history
    assert out["search_query"] == "limitations of dense retrieval"
    assert answer.queries[-1] == "limitations of dense retrieval"


async def test_sessions_are_isolated():
    answer, llm = _FakeAnswer(), _FakeLLM()
    chat = ChatOrchestrator(answer, llm)
    await chat.chat("a", "first")
    out = await chat.chat("b", "second")  # different session, no history -> no rewrite
    assert llm.calls == 0
    assert out["search_query"] == "second"
