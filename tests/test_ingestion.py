"""Unit tests for the ingestion preprocessor registry (routing + text passthrough)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ingestion.image import ImagePreprocessor
from ingestion.registry import build_registry


class _StubAnalyzer:
    """A fixed-output ImageAnalyzer for testing the fusion, with no model or network."""

    def __init__(self, label: str, text: str) -> None:
        self.label = label
        self._text = text

    async def analyze(self, image: bytes) -> str:
        return self._text


async def test_text_file_passes_through(tmp_path: Path):
    f = tmp_path / "note.txt"
    f.write_text("hello world", encoding="utf-8")
    doc = await build_registry().preprocess(f)
    assert doc.modality == "text"
    assert doc.text == "hello world"
    assert doc.source == "note.txt"


async def test_unknown_extension_falls_back_to_text(tmp_path: Path):
    f = tmp_path / "data.xyz"
    f.write_text("raw text", encoding="utf-8")
    doc = await build_registry().preprocess(f)
    assert doc.modality == "text"
    assert doc.text == "raw text"


async def test_image_preprocessor_fuses_analyzers(tmp_path: Path):
    f = tmp_path / "shot.png"
    f.write_bytes(b"\x89PNG\r\n")
    pre = ImagePreprocessor(
        [_StubAnalyzer("", "a login screen"), _StubAnalyzer("Text", "Sign in")]
    )
    doc = await pre.process(f)
    assert doc.modality == "image"
    assert doc.original_path == str(f)
    assert doc.text == "a login screen\n\nText: Sign in"


async def test_image_preprocessor_skips_empty_analyzers(tmp_path: Path):
    f = tmp_path / "shot.png"
    f.write_bytes(b"\x89PNG\r\n")
    pre = ImagePreprocessor([_StubAnalyzer("", "just a photo"), _StubAnalyzer("Text", "")])
    doc = await pre.process(f)
    assert doc.text == "just a photo"


def test_image_preprocessor_requires_an_analyzer():
    with pytest.raises(ValueError, match="at least one analyzer"):
        ImagePreprocessor([])


async def test_registry_routes_images_when_ocr_enabled():
    # easyocr's heavy model loads lazily (on first analyze), so building the registry is cheap.
    reg = build_registry(ocr_provider="easyocr")
    assert ".png" in reg._by_ext  # images now route to the OCR-backed ImagePreprocessor


def test_registry_rejects_unknown_ocr_provider():
    with pytest.raises(ValueError, match="Unknown ocr_provider"):
        build_registry(ocr_provider="tesseract")
