"""Ingest-time disambiguation: ask the model what a file leaves unclear.

A photo captioned "a man on a bike" is findable by almost nothing useful - not the rider, the
brand, or the race. The detector asks the LLM, in one call, which questions a person should answer
to make the file retrievable, with candidate answers drawn from the bucket's known entities. Each
question becomes a clarification the user answers on the Ingest tab.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.interfaces import LLMProvider
from core.json_extract import extract_json
from core.prompts import attach_marker

_PROMPT = """A file was added to a knowledge base. The Content below already describes what is
visible / present. Your job: list questions whose answers are NOT in the Content but would help
someone find this file later by who/what/where/when/why - identity and context, not description.

Ask about:
- WHO the unnamed subject is (when the Content describes someone but does not name them).
- WHERE the Content was created or what place it depicts (when not stated).
- WHEN it was created, or the date / event it captures (when not stated).
- WHAT named occasion or work this file relates to (project, paper, trip, meeting) when relevant.

NEVER ask about:
- Visible attributes the Content already describes (color of clothing, what someone is holding,
  the shape of an object). The Content already has those - they are not missing.
- Things the Content never mentions. Do not invent subjects (no bikes if no bike is shown, no
  events if no event is described).
- The same fact phrased two ways.

For candidates: only include known entities that plausibly answer THIS specific question. Empty
array is fine and expected when no known entity fits.

Known entities in the knowledge base: {entities}

Reply with JSON only. Ask 0 to 4 questions; ask 0 when the Content already names its subject and
the key identity/context facts:
{{"questions": [{{"question": "<short>", "candidates": [<entities that fit>]}}]}}

Modality: {modality}
Content:
{text}"""

# Function words + medium/subject markers ("photo", "image", "this", "shown") that describe HOW
# a question references the file, not WHAT it asks. Content nouns ("person", "event", "name",
# "brand") stay - those are the asked-for facts that distinguish questions.
_STOP = frozenset(
    "the a an of in on at to for from with about by is are was were be been being am "
    "do does did have has had can could should would will may might shall "
    "it its this that these those their they them his her your "
    "what who which when where why how whose and or but not so if then any some "
    "photo image picture video file document shown depicted seen visible here there".split()
)


def _fingerprint(question: str) -> frozenset[str]:
    """Content tokens of a question - two questions are dupes when these overlap heavily."""
    return frozenset(
        w
        for raw in question.lower().split()
        if (w := "".join(c for c in raw if c.isalnum())) and w not in _STOP and len(w) > 2
    )


def _is_duplicate(a: frozenset[str], b: frozenset[str]) -> bool:
    """A question is a dup of an earlier one when their content tokens overlap by >=75%.

    Conservative on purpose - "name of the person" and "event of the person" share {person} but ask
    for distinct facts; the dedup should only kill genuine rephrasings of the same question.
    """
    if not a or not b:
        return not a and not b  # both empty (only stopwords) -> consider them the same shape
    return len(a & b) / min(len(a), len(b)) >= 0.75


@dataclass(frozen=True)
class Question:
    """One thing the model wants clarified, with candidate answers from the bucket's entities."""

    question: str
    candidates: list[str] = field(default_factory=list)


class AmbiguityDetector:
    """One LLM call per file: what should a person clarify to make this file findable?"""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def analyze(
        self, text: str, modality: str, entities: list[str], attach: str | None = None
    ) -> list[Question]:
        """Questions to put to the user (empty when the file already states what's needed)."""
        prompt = _PROMPT.format(
            modality=modality, text=text[:2000], entities=", ".join(entities) or "(none yet)"
        ) + attach_marker(attach)
        try:
            data = extract_json(await self._llm.generate(prompt))
        except Exception:
            return []
        raw = data.get("questions")
        if not isinstance(raw, list):
            return []
        known = set(entities)
        out: list[Question] = []
        seen: list[frozenset[str]] = []
        for item in raw[:6]:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question") or "").strip()
            if not question:
                continue
            fp = _fingerprint(question)
            if any(_is_duplicate(fp, s) for s in seen):
                continue
            seen.append(fp)
            cands = [s for c in (item.get("candidates") or []) if (s := str(c).strip()) in known]
            out.append(Question(question=question, candidates=cands))
            if len(out) >= 4:
                break
        return out
