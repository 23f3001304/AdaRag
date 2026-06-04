"""Plain-text / markdown preprocessor: the file is already its own text surrogate."""

from __future__ import annotations

from pathlib import Path

from ingestion.base import ProcessedDoc


class TextPreprocessor:
    """Reads a text/markdown file straight through as its own surrogate."""

    extensions = (".txt", ".md")

    def process(self, path: Path) -> ProcessedDoc:
        return ProcessedDoc(path.name, "text", path.read_text(encoding="utf-8"), str(path))
