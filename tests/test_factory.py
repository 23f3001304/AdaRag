"""Unit tests for ProviderFactory vision wiring (construction is lazy — no network or models)."""

from __future__ import annotations

import pytest

from core.config import Settings
from providers.factory import ProviderFactory


def _vision(provider: str):
    # init kwargs override any local .env, so each provider is exercised deterministically
    return ProviderFactory(Settings(vision_provider=provider, vision_model="m")).vision()


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
    with pytest.raises(ValueError, match="Unsupported vision_provider"):
        _vision("anthropic")
