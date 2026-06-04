"""Preprocessor registry: route a file to its modality preprocessor by extension."""

from __future__ import annotations

from pathlib import Path

from core.interfaces import VisionProvider
from ingestion.audio import AudioPreprocessor
from ingestion.base import Preprocessor, ProcessedDoc
from ingestion.image import ImagePreprocessor
from ingestion.pdf import PdfPreprocessor
from ingestion.text import TextPreprocessor


class PreprocessorRegistry:
    """Maps file extensions to preprocessors; unknown extensions fall back to plain text."""

    def __init__(self, preprocessors: list[Preprocessor], fallback: Preprocessor) -> None:
        self._fallback = fallback
        self._by_ext = {ext: pp for pp in preprocessors for ext in pp.extensions}

    async def preprocess(self, path: Path) -> ProcessedDoc:
        return await self._by_ext.get(path.suffix.lower(), self._fallback).process(path)


def build_registry(vision: VisionProvider | None = None) -> PreprocessorRegistry:
    """Default registry: text + PDF, plus image captioning when a vision provider is supplied."""
    text = TextPreprocessor()
    preprocessors: list[Preprocessor] = [text, PdfPreprocessor(), AudioPreprocessor()]
    if vision is not None:
        preprocessors.append(ImagePreprocessor(vision))
    return PreprocessorRegistry(preprocessors, fallback=text)
