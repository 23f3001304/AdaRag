"""Ingestion preprocessors: normalize a source file into a text surrogate for the index."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ProcessedDoc:
    """A source normalized for indexing: a text surrogate, plus the preserved original."""

    source: str
    modality: str
    text: str
    original_path: str | None = None


class Preprocessor(Protocol):
    """Turns a file of some modality into a ProcessedDoc (text surrogate + preserved original)."""

    extensions: tuple[str, ...]

    async def process(self, path: Path) -> ProcessedDoc: ...


class ImageAnalyzer(Protocol):
    """One way of turning an image into searchable text (a caption, OCR'd text, object tags...).

    Several analyzers compose into one image surrogate, so each is a focused, swappable lens
    (claude-cli vision, a local Florence-2 model, a dedicated OCR engine) behind one contract.
    """

    label: str  # section heading for this analyzer's text ("Text", "Objects"); "" = no prefix

    async def analyze(self, image: bytes) -> str:
        """Return text describing the image (empty string when this lens finds nothing)."""
        ...
