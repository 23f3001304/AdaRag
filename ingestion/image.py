"""Image preprocessor: one or more analyzers turn an image into a fused text surrogate.

Each ``ImageAnalyzer`` is a focused lens (a caption, OCR'd text, object tags); the preprocessor
runs them all and joins their non-empty outputs, so the surrogate can blend a vision LLM's
description with a local model's verbatim OCR. The original file is always preserved.
"""

from __future__ import annotations

from pathlib import Path

from core.interfaces import VisionProvider
from ingestion.base import ImageAnalyzer, ProcessedDoc

_CAPTION_PROMPT = (
    "Describe this image for search retrieval, and transcribe any text in it verbatim. "
    "Reply with 2-4 plain sentences, no preamble."
)


class CaptionAnalyzer:
    """Adapts a ``VisionProvider`` (e.g. claude-cli) into a captioning + OCR analyzer."""

    label = ""  # the caption is the lead text, so it carries no section heading

    def __init__(self, vision: VisionProvider, prompt: str = _CAPTION_PROMPT) -> None:
        self._vision = vision
        self._prompt = prompt

    async def analyze(self, image: bytes) -> str:
        return (await self._vision.describe(image, self._prompt)).strip()


class ImagePreprocessor:
    """Fuses every analyzer's text into one image surrogate; the original is preserved."""

    extensions = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")

    def __init__(self, analyzers: list[ImageAnalyzer]) -> None:
        if not analyzers:
            raise ValueError("ImagePreprocessor needs at least one analyzer")
        self._analyzers = analyzers

    async def process(self, path: Path) -> ProcessedDoc:
        image = path.read_bytes()
        parts: list[str] = []
        for analyzer in self._analyzers:
            text = (await analyzer.analyze(image)).strip()
            if text:
                parts.append(f"{analyzer.label}: {text}" if analyzer.label else text)
        return ProcessedDoc(path.name, "image", "\n\n".join(parts), str(path))
