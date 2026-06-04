"""Unit tests for the ingestion preprocessor registry (routing + text passthrough)."""

from __future__ import annotations

from pathlib import Path

from ingestion.registry import build_registry


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
