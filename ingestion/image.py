"""Image preprocessor: a vision provider captions + OCRs the image as its text surrogate."""

from __future__ import annotations

from pathlib import Path

from core.interfaces import VisionProvider
from ingestion.base import ProcessedDoc

_CAPTION_PROMPT = (
    "Describe this image for search retrieval, and transcribe any text in it verbatim. "
    "Reply with 2-4 plain sentences, no preamble."
)


class ImagePreprocessor:
    """Captions an image (and OCRs its text) via a vision provider; the original is preserved."""

    extensions = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")

    def __init__(self, vision: VisionProvider) -> None:
        self._vision = vision

    async def process(self, path: Path) -> ProcessedDoc:
        caption = await self._vision.describe(path.read_bytes(), _CAPTION_PROMPT)
        return ProcessedDoc(path.name, "image", caption.strip(), str(path))
