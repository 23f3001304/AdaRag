"""OCR image analyzer: EasyOCR reads text from an image into a searchable surrogate fragment.

A dedicated OCR engine transcribes screenshots/scans/diagrams verbatim and locally (on the GPU),
where a vision LLM only summarizes. Local + free also keeps the cost-per-MB low. The model is a
heavy native lib, so it is imported and loaded lazily and run off the event loop.
"""

from __future__ import annotations

import asyncio
from typing import Any


class EasyOcrAnalyzer:
    """Transcribes an image's text with EasyOCR; an ImageAnalyzer (label = "Text")."""

    label = "Text"

    def __init__(self, languages: tuple[str, ...] = ("en",), gpu: bool = True) -> None:
        self._languages = list(languages)
        self._gpu = gpu
        self._reader: Any | None = None

    def _load(self) -> Any:
        if self._reader is None:
            import easyocr  # deferred: heavy native lib + first-run model download

            self._reader = easyocr.Reader(self._languages, gpu=self._gpu)
        return self._reader

    def _read(self, image: bytes) -> str:
        # detail=0 -> plain strings; paragraph=True merges nearby boxes into readable lines
        lines = self._load().readtext(image, detail=0, paragraph=True)
        return "\n".join(s.strip() for s in lines if s and s.strip())

    async def analyze(self, image: bytes) -> str:
        return await asyncio.to_thread(self._read, image)
