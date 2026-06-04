"""Code chunking by AST: split source at top-level definitions via tree-sitter (DESIGN.md)."""

from __future__ import annotations

from typing import Any

from chunking.base import Chunk

# Top-level definition nodes across common grammars (Python first; degrades for others).
_DEF_TYPES = {
    "function_definition",
    "function_declaration",
    "method_definition",
    "class_definition",
    "class_declaration",
    "decorated_definition",
}


class CodeChunker:
    """Chunks code by top-level AST node: each function/class becomes a chunk, and runs of
    module-level statements (imports, constants) are grouped. Tree-sitter parser, lazy-loaded."""

    def __init__(self, language: str = "python") -> None:
        self._language = language
        self._parser: Any | None = None

    def _load(self) -> Any:
        if self._parser is None:
            from tree_sitter import Parser  # deferred: pulls the native parser
            from tree_sitter_language_pack import get_language

            self._parser = Parser(get_language(self._language))
        return self._parser

    def chunk(self, text: str) -> list[Chunk]:
        data = text.encode("utf-8")
        root = self._load().parse(data).root_node
        chunks: list[Chunk] = []
        run: list[tuple[int, int]] = []
        for node in root.children:
            if node.type in _DEF_TYPES:
                self._flush(chunks, data, run)
                run = []
                self._emit(chunks, data, node.start_byte, node.end_byte)
            else:
                run.append((node.start_byte, node.end_byte))
        self._flush(chunks, data, run)
        if chunks:
            return chunks
        stripped = text.strip()
        return [Chunk(0, stripped, 0, len(data))] if stripped else []

    def _flush(self, chunks: list[Chunk], data: bytes, run: list[tuple[int, int]]) -> None:
        if run:
            self._emit(chunks, data, run[0][0], run[-1][1])

    @staticmethod
    def _emit(chunks: list[Chunk], data: bytes, start: int, end: int) -> None:
        snippet = data[start:end].decode("utf-8", errors="ignore").strip()
        if snippet:
            chunks.append(Chunk(len(chunks), snippet, start, end))
