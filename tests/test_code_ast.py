"""Unit tests for the tree-sitter code chunker."""

from __future__ import annotations

from chunking.code_ast import CodeChunker


def test_chunks_by_top_level_definition():
    code = (
        "import os\n\ndef foo(x):\n    return x + 1\n\n"
        "class Bar:\n    def m(self):\n        return 2\n"
    )
    texts = [c.text for c in CodeChunker().chunk(code)]
    assert any(t.startswith("import os") for t in texts)
    assert any(t.startswith("def foo") for t in texts)
    assert any(t.startswith("class Bar") for t in texts)
    assert len(texts) == 3


def test_keeps_a_class_whole():
    code = "class Big:\n    def a(self):\n        return 1\n    def b(self):\n        return 2\n"
    chunks = CodeChunker().chunk(code)
    assert len(chunks) == 1
    assert "def a" in chunks[0].text and "def b" in chunks[0].text


def test_blank_code_yields_no_chunks():
    assert CodeChunker().chunk("   \n") == []
