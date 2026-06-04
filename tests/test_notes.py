"""Unit tests for the notes chunker."""

from __future__ import annotations

from chunking.notes import NotesChunker


def test_packs_blocks_under_cap_into_one_chunk():
    text = "buy milk\n\ncall alice\n"
    chunks = NotesChunker(max_chars=100).chunk(text)
    assert len(chunks) == 1
    assert "buy milk" in chunks[0].text
    assert "call alice" in chunks[0].text


def test_small_cap_splits_into_multiple_chunks():
    text = "- a\n- b\n\n- c\n- d\n\n- e\n"
    chunks = NotesChunker(max_chars=12).chunk(text)
    assert len(chunks) >= 2
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_blank_only_text_yields_no_chunks():
    assert NotesChunker().chunk("\n\n   \n") == []
