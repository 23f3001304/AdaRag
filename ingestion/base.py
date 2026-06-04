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

    def process(self, path: Path) -> ProcessedDoc: ...
