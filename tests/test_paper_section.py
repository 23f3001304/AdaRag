"""Unit tests for the paper-section chunker."""

from __future__ import annotations

from chunking.paper_section import PaperSectionChunker


def test_one_chunk_per_section():
    text = "# Intro\nalpha alpha.\n\n# Methods\nbeta beta.\n\n## Results\ngamma.\n"
    chunks = PaperSectionChunker().chunk(text)
    assert len(chunks) == 3
    assert chunks[0].text.startswith("# Intro")
    assert chunks[1].text.startswith("# Methods")
    assert [c.index for c in chunks] == [0, 1, 2]


def test_long_section_falls_back_to_windows():
    text = "# Big\n" + ("x " * 2000)
    chunks = PaperSectionChunker(max_chars=800).chunk(text)
    assert len(chunks) > 1


def test_preamble_before_first_heading_is_kept():
    text = "intro line with no heading.\n\n# Section\nbody.\n"
    chunks = PaperSectionChunker().chunk(text)
    assert chunks[0].text.startswith("intro line")
    assert chunks[1].text.startswith("# Section")
