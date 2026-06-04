"""Provider factory: builds the configured LLM and embedding providers from Settings (BYOK).

Implementations are imported lazily so callers only pay for the provider they actually use
(notably the local embedder's torch import).
"""

from __future__ import annotations

from core.config import Settings
from core.interfaces import EmbeddingProvider, LLMProvider, VisionProvider


class ProviderFactory:
    """Builds providers per the BYOK configuration."""

    def __init__(self, settings: Settings) -> None:
        self._s = settings

    def llm(self) -> LLMProvider:
        s = self._s
        if s.llm_provider == "anthropic":
            from providers.anthropic import AnthropicLLM

            return AnthropicLLM(s.anthropic_api_key, s.llm_model)
        if s.llm_provider == "openai":
            from providers.openai import OpenAILLM

            return OpenAILLM(s.openai_api_key, s.llm_model)
        if s.llm_provider == "ollama":
            from providers.ollama import OllamaLLM

            return OllamaLLM(s.ollama_base_url, s.llm_model)
        if s.llm_provider == "openrouter":
            from providers.openai import OpenAILLM

            return OpenAILLM(
                s.openrouter_api_key, s.llm_model, base_url="https://openrouter.ai/api/v1"
            )
        if s.llm_provider == "claude-cli":
            from providers.cli import ClaudeCodeLLM

            return ClaudeCodeLLM(s.llm_model, s.claude_cli_path)
        if s.llm_provider == "gemini-cli":
            from providers.cli import GeminiCLILLM

            return GeminiCLILLM(s.llm_model, s.gemini_cli_path)
        raise ValueError(f"Unknown llm_provider: {s.llm_provider!r}")

    def embeddings(self) -> EmbeddingProvider:
        if self._s.embedding_provider == "local":
            from providers.local_embeddings import BGEM3Embeddings

            return BGEM3Embeddings(self._s.embedding_model)
        raise ValueError(f"Unsupported embedding_provider: {self._s.embedding_provider!r}")

    def vision(self) -> VisionProvider:
        s = self._s
        if s.vision_provider == "claude-cli":
            from providers.cli import ClaudeCliVision

            return ClaudeCliVision(s.vision_model, s.claude_cli_path)
        if s.vision_provider == "gemini-cli":
            from providers.cli import GeminiCliVision

            return GeminiCliVision(s.vision_model, s.gemini_cli_path)
        if s.vision_provider == "ollama":
            from providers.ollama import OllamaVision

            return OllamaVision(s.ollama_base_url, s.vision_model)
        raise ValueError(f"Unsupported vision_provider: {s.vision_provider!r}")
