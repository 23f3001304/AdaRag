"""Document profiler: classify text to choose a chunking strategy (DESIGN.md adaptive ingestion)."""

from __future__ import annotations

import re
from enum import StrEnum

# Strong code signals only — definitions, imports, arrows. Deliberately NOT braces/semicolons or
# indentation, which formula-heavy prose (LaTeX, math) trips over and gets misread as code.
_CODE_LINE = re.compile(
    r"\bdef\s+\w+\s*\(|\bclass\s+\w+\s*[:(]|^\s*(?:import|from)\s+\w|\bfunction\s+\w+\s*\(|=>"
)
_HEADING = re.compile(r"^(#{1,6}\s+\S|\d+(\.\d+)*\.?\s+[A-Z])")
_BULLET = re.compile(r"^\s*([-*•]|\d+[.)])\s+\S")


class DocProfile(StrEnum):
    """Coarse document type that selects a chunking strategy."""

    CODE = "code"
    PAPER = "paper"
    NOTES = "notes"
    PROSE = "prose"


class DocumentProfiler:
    """Content heuristics: code by syntax, papers by headings, notes by bullets; else prose."""

    def __init__(self, code_threshold: float = 0.15, min_headings: int = 3) -> None:
        self._code_threshold = code_threshold
        self._min_headings = min_headings

    def profile(self, text: str) -> DocProfile:
        """Classify a document from its content (cheap, deterministic, no model call)."""
        lines = [ln for ln in text.splitlines() if ln.strip()]
        if not lines:
            return DocProfile.PROSE
        if self._fraction(lines, _CODE_LINE) >= self._code_threshold:
            return DocProfile.CODE
        if sum(bool(_HEADING.match(ln)) for ln in lines) >= self._min_headings:
            return DocProfile.PAPER
        if self._fraction(lines, _BULLET) >= 0.4:
            return DocProfile.NOTES
        return DocProfile.PROSE

    @staticmethod
    def _fraction(lines: list[str], pattern: re.Pattern[str]) -> float:
        return sum(bool(pattern.search(ln)) for ln in lines) / len(lines)
