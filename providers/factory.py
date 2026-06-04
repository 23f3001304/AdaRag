"""Provider factory: builds the configured providers from Settings (BYOK selection).

Implementations are imported lazily so callers that only need one provider (or none)
don't pay for the others' dependencies — notably the local embedder's torch import.
"""

from __future__ import annotations

from core.config import Settings
from core.interfaces import EmbeddingProvider, LLMProvider


def build_llm(settings: Settings) -> LLMProvider:
    """Construct the LLM provider named by settings.llm_provider."""
    provider = settings.llm_provider
    if provider == "anthropic":
        from providers.anthropic import AnthropicLLM

        return AnthropicLLM(settings.anthropic_api_key, settings.llm_model)
    if provider == "openai":
        from providers.openai import OpenAILLM

        return OpenAILLM(settings.openai_api_key, settings.llm_model)
    if provider == "ollama":
        from providers.ollama import OllamaLLM

        return OllamaLLM(settings.ollama_base_url, settings.llm_model)
    if provider == "openrouter":
        from providers.openai import OpenAILLM  # OpenRouter speaks the OpenAI API

        return OpenAILLM(
            settings.openrouter_api_key,
            settings.llm_model,
            base_url="https://openrouter.ai/api/v1",
        )
    if provider == "claude-cli":
        from providers.cli import ClaudeCodeLLM  # shells out to the Claude Code CLI

        return ClaudeCodeLLM(settings.llm_model, settings.claude_cli_path)
    if provider == "gemini-cli":
        from providers.cli import GeminiCLILLM  # shells out to the Gemini CLI

        return GeminiCLILLM(settings.llm_model, settings.gemini_cli_path)
    raise ValueError(f"Unknown llm_provider: {provider!r}")


def build_embeddings(settings: Settings) -> EmbeddingProvider:
    """Construct the embedding provider named by settings.embedding_provider."""
    if settings.embedding_provider == "local":
        from providers.local_embeddings import BGEM3Embeddings  # lazy: imports torch

        return BGEM3Embeddings(settings.embedding_model)
    raise ValueError(f"Unsupported embedding_provider: {settings.embedding_provider!r} (only 'local')")
