"""Unit tests for the document profiler (content-based chunking-strategy selection)."""

from __future__ import annotations

from chunking.profile import DocProfile, DocumentProfiler

P = DocumentProfiler()


def test_detects_code_by_syntax():
    code = "import os\n\ndef foo(x):\n    return x + 1\n\nclass Bar:\n    pass\n"
    assert P.profile(code) == DocProfile.CODE


def test_detects_paper_by_headings():
    paper = (
        "# Introduction\nText about things.\n\n"
        "## Methods\nWe did stuff.\n\n## Results\nIt worked.\n"
    )
    assert P.profile(paper) == DocProfile.PAPER


def test_detects_notes_by_bullets():
    notes = "- buy milk\n- call alice\n* finish the report\n- 3pm meeting\n"
    assert P.profile(notes) == DocProfile.NOTES


def test_defaults_to_prose():
    prose = (
        "Dense retrieval turns each chunk into a vector; it captures meaning but blurs detail.\n"
    )
    assert P.profile(prose) == DocProfile.PROSE


def test_empty_text_is_prose():
    assert P.profile("   \n\n  ") == DocProfile.PROSE


def test_formula_prose_is_not_code():
    text = (
        "The weight is {\\displaystyle w_{t,d}}; it grows with the term frequency.\n"
        "Each document maps to a vector in the space, and similarity follows.\n"
        "The function of the model is to rank passages by their relevance.\n"
    )
    assert P.profile(text) != DocProfile.CODE
