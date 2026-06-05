"""Unit tests for the chat IntentRouter (fake LLM, no stack)."""

from __future__ import annotations

from orchestrator.router import IntentRouter


class _FakeLLM:
    """Echoes a fixed verdict and records the prompt it saw."""

    model = "fake"

    def __init__(self, verdict: str) -> None:
        self._verdict = verdict
        self.prompt = ""

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        self.prompt = prompt
        return self._verdict


async def test_ingest_intent_is_detected():
    router = IntentRouter(_FakeLLM("ingest"))
    assert await router.is_ingest("please add this to the knowledge base") is True


async def test_question_is_not_ingest():
    router = IntentRouter(_FakeLLM("ask"))
    assert await router.is_ingest("what does this document say?") is False


async def test_verdict_is_normalized():
    router = IntentRouter(_FakeLLM("  Ingest.\n"))  # padded/capitalized still classifies as ingest
    assert await router.is_ingest("save it") is True


async def test_message_reaches_the_prompt():
    llm = _FakeLLM("ask")
    await IntentRouter(llm).is_ingest("hello there")
    assert "hello there" in llm.prompt
