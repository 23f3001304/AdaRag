"""Provider adapter registries: map a provider name to a builder, so new backends — including
a user's own — plug in without editing the factory (Open/Closed).

Built-ins register at import time (bottom of this file). To add your own, write a module that calls
``register_vision("myname", lambda s: MyVision(...))`` (or ``register_llm``), name it in the
``provider_plugins`` setting, and select it via ``vision_provider=myname``. A builder takes the
``Settings`` and returns anything satisfying the ``VisionProvider`` / ``LLMProvider`` protocol — no
edits to this codebase required.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable

from core.config import Settings
from core.interfaces import LLMProvider, VisionProvider

LLMBuilder = Callable[[Settings], LLMProvider]
VisionBuilder = Callable[[Settings], VisionProvider]

_LLM: dict[str, LLMBuilder] = {}
_VISION: dict[str, VisionBuilder] = {}
_LOADED: set[str] = set()


def register_llm(name: str, builder: LLMBuilder) -> None:
    """Register (or override) an LLM provider builder under ``name``."""
    _LLM[name] = builder


def register_vision(name: str, builder: VisionBuilder) -> None:
    """Register (or override) a vision provider builder under ``name``."""
    _VISION[name] = builder


def load_plugins(spec: str) -> None:
    """Import each comma-separated module path so its register_* calls run (idempotent)."""
    for module in (m.strip() for m in spec.split(",") if m.strip()):
        if module not in _LOADED:
            importlib.import_module(module)
            _LOADED.add(module)


def build_llm(settings: Settings) -> LLMProvider:
    """Build the configured LLM provider; raises with the known names if it isn't registered."""
    builder = _LLM.get(settings.llm_provider)
    if builder is None:
        raise ValueError(f"Unknown llm_provider: {settings.llm_provider!r}. Have: {sorted(_LLM)}")
    return builder(settings)


def build_vision(settings: Settings) -> VisionProvider:
    """Build the configured vision provider; raises with the known names if it isn't registered."""
    builder = _VISION.get(settings.vision_provider)
    if builder is None:
        have = sorted(_VISION)
        raise ValueError(f"Unknown vision_provider: {settings.vision_provider!r}. Have: {have}")
    return builder(settings)


# --- built-in registrations (provider imports stay lazy so optional deps load only when chosen) ---


def _anthropic_llm(s: Settings) -> LLMProvider:
    from providers.anthropic import AnthropicLLM

    return AnthropicLLM(s.anthropic_api_key, s.llm_model)


def _openai_llm(s: Settings) -> LLMProvider:
    from providers.openai import OpenAILLM

    return OpenAILLM(s.openai_api_key, s.llm_model)


def _openrouter_llm(s: Settings) -> LLMProvider:
    from providers.openai import OpenAILLM

    return OpenAILLM(s.openrouter_api_key, s.llm_model, base_url="https://openrouter.ai/api/v1")


def _ollama_llm(s: Settings) -> LLMProvider:
    from providers.ollama import OllamaLLM

    return OllamaLLM(s.ollama_base_url, s.llm_model)


def _claude_cli_llm(s: Settings) -> LLMProvider:
    from providers.cli import ClaudeCodeLLM

    return ClaudeCodeLLM(s.llm_model, s.claude_cli_path)


def _gemini_cli_llm(s: Settings) -> LLMProvider:
    from providers.cli import GeminiCLILLM

    return GeminiCLILLM(s.llm_model, s.gemini_cli_path)


def _claude_cli_vision(s: Settings) -> VisionProvider:
    from providers.cli import ClaudeCliVision

    return ClaudeCliVision(s.vision_model, s.claude_cli_path)


def _gemini_cli_vision(s: Settings) -> VisionProvider:
    from providers.cli import GeminiCliVision

    return GeminiCliVision(s.vision_model, s.gemini_cli_path)


def _ollama_vision(s: Settings) -> VisionProvider:
    from providers.ollama import OllamaVision

    return OllamaVision(s.ollama_base_url, s.vision_model)


def _bridge_llm(s: Settings) -> LLMProvider:
    from providers.http_bridge import HttpBridgeLLM

    return HttpBridgeLLM(s.cli_bridge_url, s.llm_model)


def _bridge_vision(s: Settings) -> VisionProvider:
    from providers.http_bridge import HttpBridgeVision

    return HttpBridgeVision(s.cli_bridge_url, s.vision_model)


register_llm("anthropic", _anthropic_llm)
register_llm("openai", _openai_llm)
register_llm("openrouter", _openrouter_llm)
register_llm("ollama", _ollama_llm)
register_llm("claude-cli", _claude_cli_llm)
register_llm("gemini-cli", _gemini_cli_llm)
register_llm("cli-bridge", _bridge_llm)
register_vision("claude-cli", _claude_cli_vision)
register_vision("gemini-cli", _gemini_cli_vision)
register_vision("ollama", _ollama_vision)
register_vision("cli-bridge", _bridge_vision)
