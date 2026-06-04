"""Metadata enrichment: per-chunk entities, dates, and keyphrases.

Entities and dates become payload metadata (for the query layer's filters); keyphrases are appended
to the embedded/reranked text to boost the sparse (lexical) signal for a chunk's salient terms.
LLM-based here for zero extra dependencies; swappable for spaCy + YAKE (see DESIGN.md) later.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.interfaces import LLMProvider
from core.json_extract import extract_json

_PROMPT = """Extract search metadata from the passage. Reply with JSON only — three string arrays:
{{"entities": [...], "dates": [...], "keyphrases": [...]}}.
- entities: named things (people, organizations, products, technologies, proper nouns).
- dates: any dates or explicit time references, copied as written.
- keyphrases: 3-6 short phrases naming the passage's key topics, for lexical search.

Passage:
{text}"""


@dataclass(frozen=True)
class ChunkMetadata:
    """Salient terms: entities/dates for payload filters, keyphrases for the sparse-index boost."""

    entities: list[str] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)
    keyphrases: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.entities or self.dates or self.keyphrases)

    def sparse_terms(self) -> str:
        """Keyphrases + entities, for appending to chunk text (sparse-signal boost)."""
        return " ".join(self.keyphrases + self.entities)


class MetadataEnricher:
    """Extracts entities, dates, and keyphrases from a chunk in one structured LLM call."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def extract(self, text: str) -> ChunkMetadata:
        data = extract_json(await self._llm.generate(_PROMPT.format(text=text)))
        return ChunkMetadata(
            entities=_str_list(data.get("entities")),
            dates=_str_list(data.get("dates")),
            keyphrases=_str_list(data.get("keyphrases")),
        )


def _str_list(value: object) -> list[str]:
    """Coerce an LLM JSON field into a list of trimmed, non-empty strings (drops null/blank)."""
    if not isinstance(value, list):
        return []
    trimmed = [str(v).strip() for v in value if v is not None]
    return [s for s in trimmed if s]
