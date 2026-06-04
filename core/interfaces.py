"""Layer interfaces — the contracts the pipeline depends on (Dependency Inversion).

Concrete implementations live in the top-level layer packages (e.g. providers/).
For now this defines the three BYOK provider roles; other layer interfaces join later.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Turns text into dense vectors (sparse vectors arrive in Phase 1)."""

    dim: int

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into dense vectors of length ``dim``."""
        ...


@runtime_checkable
class LLMProvider(Protocol):
    """Text generation for answers, query rewriting, and enrichment."""

    model: str

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        """Return a completion for a single prompt."""
        ...


@runtime_checkable
class VisionProvider(Protocol):
    """Reads images: captioning at ingest, and seeing the image at answer time."""

    model: str

    async def describe(self, image: bytes, prompt: str) -> str:
        """Return text about an image given an instruction."""
        ...
