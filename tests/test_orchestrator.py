"""Unit tests for the ChatOrchestrator's multi-turn contextualization (fakes, no stack)."""

from __future__ import annotations

from orchestrator.chat import ChatOrchestrator


class _FakeAnswer:
    """Records the queries (and any skill overrides) it was asked, and echoes a cited answer."""

    def __init__(self) -> None:
        self.queries: list[str] = []
        self.overrides: list[tuple[str | None, int | None]] = []

    async def answer(
        self, query: str, *, persona: str | None = None, top_k: int | None = None
    ) -> dict:
        self.queries.append(query)
        self.overrides.append((persona, top_k))
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


async def test_greeting_answers_without_retrieval():
    answer, llm = _FakeAnswer(), _FakeLLM("Hi! Ask me about your docs.")
    out = await ChatOrchestrator(answer, llm).chat("s1", "hi")
    assert answer.queries == []  # a greeting never reaches the answer service
    assert out["citations"] == []
    assert out["search_query"] is None
    assert out["answer"] == "Hi! Ask me about your docs."
    assert llm.calls == 1  # one direct reply, no contextualization or retrieval


async def test_real_question_still_retrieves():
    answer, llm = _FakeAnswer(), _FakeLLM()
    await ChatOrchestrator(answer, llm).chat("s1", "what is reranking?")
    assert answer.queries == ["what is reranking?"]  # not chitchat -> retrieves


async def test_skill_overrides_reach_the_answer_service():
    answer, llm = _FakeAnswer(), _FakeLLM()
    chat = ChatOrchestrator(answer, llm)
    await chat.chat("s1", "what is RRF?", persona="Answer as a terse expert.", top_k=12)
    assert answer.overrides == [("Answer as a terse expert.", 12)]


async def test_no_skill_passes_no_overrides():
    answer, llm = _FakeAnswer(), _FakeLLM()
    await ChatOrchestrator(answer, llm).chat("s1", "plain question")
    assert answer.overrides == [(None, None)]
