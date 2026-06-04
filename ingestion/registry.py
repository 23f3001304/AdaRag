"""Preprocessor registry: route a file to its modality preprocessor by extension."""

from __future__ import annotations

from pathlib import Path

from core.interfaces import VisionProvider
from ingestion.audio import AudioPreprocessor
from ingestion.base import ImageAnalyzer, Preprocessor, ProcessedDoc
from ingestion.image import CaptionAnalyzer, ImagePreprocessor
from ingestion.ocr import EasyOcrAnalyzer
from ingestion.pdf import PdfPreprocessor
from ingestion.text import TextPreprocessor


class PreprocessorRegistry:
    """Maps file extensions to preprocessors; unknown extensions fall back to plain text."""

    def __init__(self, preprocessors: list[Preprocessor], fallback: Preprocessor) -> None:
        self._fallback = fallback
        self._by_ext = {ext: pp for pp in preprocessors for ext in pp.extensions}

    async def preprocess(self, path: Path) -> ProcessedDoc:
        return await self._by_ext.get(path.suffix.lower(), self._fallback).process(path)


def build_registry(
    vision: VisionProvider | None = None, ocr_provider: str = ""
) -> PreprocessorRegistry:
    """Text + PDF + audio/video, plus image analysis fusing a vision caption and/or local OCR.

    Images route to an ImagePreprocessor only when at least one analyzer is configured: a
    ``vision`` provider (caption + LLM OCR) and/or ``ocr_provider`` ("easyocr" for local OCR).
    """
    text = TextPreprocessor()
    preprocessors: list[Preprocessor] = [text, PdfPreprocessor(), AudioPreprocessor()]
    analyzers: list[ImageAnalyzer] = []
    if vision is not None:
        analyzers.append(CaptionAnalyzer(vision))
    if ocr_provider == "easyocr":
        analyzers.append(EasyOcrAnalyzer())
    elif ocr_provider not in ("", "none"):
        raise ValueError(f"Unknown ocr_provider: {ocr_provider!r}")
    if analyzers:
        preprocessors.append(ImagePreprocessor(analyzers))
    return PreprocessorRegistry(preprocessors, fallback=text)
