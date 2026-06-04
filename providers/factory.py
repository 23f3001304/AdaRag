"""Provider factory: builds the configured providers from Settings (BYOK).

LLM and vision providers resolve through the adapter registry (providers/registry.py), so new
backends — including a user's own — plug in by registering a builder, with no edits here. The
embedding provider has a single local implementation, so it is built directly.
"""

from __future__ import annotations

from core.config import Settings
from core.interfaces import EmbeddingProvider, LLMProvider, VisionProvider
from providers.registry import build_llm, build_vision, load_plugins


class ProviderFactory:
    """Builds providers per the BYOK config; LLM/vision resolve via the adapter registry."""

    def __init__(self, settings: Settings) -> None:
        self._s = settings
        load_plugins(settings.provider_plugins)  # import any user adapter modules first

    def llm(self) -> LLMProvider:
        return build_llm(self._s)

    def vision(self) -> VisionProvider:
        return build_vision(self._s)

    def embeddings(self) -> EmbeddingProvider:
        if self._s.embedding_provider == "local":
            from providers.local_embeddings import BGEM3Embeddings

            return BGEM3Embeddings(self._s.embedding_model)
        raise ValueError(f"Unsupported embedding_provider: {self._s.embedding_provider!r}")
