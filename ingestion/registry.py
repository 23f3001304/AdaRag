"""Preprocessor registry: route a file to its modality preprocessor by extension."""

from __future__ import annotations

from pathlib import Path

from ingestion.base import Preprocessor, ProcessedDoc
from ingestion.pdf import PdfPreprocessor
from ingestion.text import TextPreprocessor


class PreprocessorRegistry:
    """Maps file extensions to preprocessors; unknown extensions fall back to plain text."""

    def __init__(self, preprocessors: list[Preprocessor], fallback: Preprocessor) -> None:
        self._fallback = fallback
        self._by_ext = {ext: pp for pp in preprocessors for ext in pp.extensions}

    def preprocess(self, path: Path) -> ProcessedDoc:
        return self._by_ext.get(path.suffix.lower(), self._fallback).process(path)


def build_registry() -> PreprocessorRegistry:
    """Default registry: text + PDF (more modalities added per later build step)."""
    text = TextPreprocessor()
    return PreprocessorRegistry([text, PdfPreprocessor()], fallback=text)
