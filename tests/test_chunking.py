"""Unit tests for the naive chunker (pure logic — no infra or GPU needed)."""

from __future__ import annotations

import pytest

from chunking.naive import naive_chunks


def test_splits_into_overlapping_windows():
    chunks = naive_chunks("a" * 1200, size=512, overlap=64)
    assert len(chunks) == 3
    assert [(c.start, c.end) for c in chunks] == [(0, 512), (448, 960), (896, 1200)]
    assert [c.index for c in chunks] == [0, 1, 2]


def test_short_text_is_a_single_chunk():
    chunks = naive_chunks("hello world", size=512, overlap=64)
    assert len(chunks) == 1
    assert chunks[0].text == "hello world"
    assert (chunks[0].start, chunks[0].end) == (0, 11)


def test_overlap_carries_text_across_windows():
    chunks = naive_chunks("0123456789", size=4, overlap=2)  # step = 2
    assert [c.text for c in chunks] == ["0123", "2345", "4567", "6789"]


def test_empty_or_whitespace_yields_nothing():
    assert naive_chunks("", 512, 64) == []
    assert naive_chunks("   \n  ", 512, 64) == []


@pytest.mark.parametrize("size,overlap", [(0, 0), (-1, 0), (10, 10), (10, 12)])
def test_invalid_params_raise(size, overlap):
    with pytest.raises(ValueError):
        naive_chunks("some text", size, overlap)
