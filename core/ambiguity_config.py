"""Runtime-switchable model for ingest ambiguity detection.

The Settings page picks which provider+model judges whether a file's subject is identifiable. The
choice lives here, in memory on the API (live, no restart, no bridge dependency at startup); when
unset, detection falls back to the bucket's default LLM.
"""

from __future__ import annotations

from collections.abc import Callable

from core.interfaces import LLMProvider
from enrichment.ambiguity import AmbiguityDetector


class AmbiguityConfig:
    """Holds the chosen ambiguity model and lazily builds (and caches) a detector for it."""

    def __init__(
        self, default_llm: LLMProvider, llm_for: Callable[[str, str], LLMProvider]
    ) -> None:
        self._default = AmbiguityDetector(default_llm)
        self._llm_for = llm_for
        self._provider = ""
        self._model = ""
        self._cached: AmbiguityDetector | None = None

    def get(self) -> tuple[str, str]:
        return self._provider, self._model

    def set(self, provider: str, model: str) -> None:
        self._provider, self._model = provider.strip(), model.strip()
        self._cached = None

    def detector(self) -> AmbiguityDetector:
        """The detector for the chosen model, or the default LLM's detector when unset."""
        if not (self._provider and self._model):
            return self._default
        if self._cached is None:
            self._cached = AmbiguityDetector(self._llm_for(self._provider, self._model))
        return self._cached
