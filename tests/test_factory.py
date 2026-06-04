"""Unit tests for the provider adapter registry + factory (lazy construction, no network)."""

from __future__ import annotations

import pytest

from core.config import Settings
from providers.factory import ProviderFactory


def _vision(provider: str):
    # init kwargs override any local .env, so each provider is exercised deterministically
    return ProviderFactory(Settings(vision_provider=provider, vision_model="m")).vision()


def _llm(provider: str):
    return ProviderFactory(Settings(llm_provider=provider, llm_model="m")).llm()


def test_vision_claude_cli():
    from providers.cli import ClaudeCliVision

    assert isinstance(_vision("claude-cli"), ClaudeCliVision)


def test_vision_gemini_cli():
    from providers.cli import GeminiCliVision

    assert isinstance(_vision("gemini-cli"), GeminiCliVision)


def test_vision_ollama():
    from providers.ollama import OllamaVision

    assert isinstance(_vision("ollama"), OllamaVision)


def test_vision_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown vision_provider"):
        _vision("anthropic")


def test_llm_ollama():
    from providers.ollama import OllamaLLM

    assert isinstance(_llm("ollama"), OllamaLLM)


def test_llm_claude_cli():
    from providers.cli import ClaudeCodeLLM

    assert isinstance(_llm("claude-cli"), ClaudeCodeLLM)


def test_llm_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown llm_provider"):
        _llm("does-not-exist")


def test_cli_bridge_providers_resolve():
    from providers.http_bridge import HttpBridgeLLM, HttpBridgeVision

    assert isinstance(_llm("cli-bridge"), HttpBridgeLLM)
    assert isinstance(_vision("cli-bridge"), HttpBridgeVision)


def test_register_custom_vision_adapter():
    """A third party can register their own vision backend and select it by name."""
    from providers.registry import register_vision

    class _MyVision:
        model = "mine"

        async def describe(self, image: bytes, prompt: str) -> str:
            return "described"

    register_vision("custom-test", lambda s: _MyVision())
    provider = _vision("custom-test")
    assert isinstance(provider, _MyVision)
