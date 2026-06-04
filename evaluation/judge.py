"""LLM-as-judge generation metrics: faithfulness + answer relevance (lightweight, RAGAS-style)."""

from __future__ import annotations

from dataclasses import dataclass

from core.interfaces import LLMProvider
from evaluation.datasets import extract_json


@dataclass(frozen=True)
class GenerationScores:
    faithfulness: float
    answer_relevance: float


_JUDGE_PROMPT = """Score the answer from 0.0 to 1.0 on two axes:
- faithfulness: is every claim supported by the context, with nothing invented?
- answer_relevance: does the answer actually address the question?
Reply as JSON only: {{"faithfulness": 0.0, "answer_relevance": 0.0}}

Question: {question}
Context: {context}
Answer: {answer}"""


def _clip01(value: object) -> float:
    try:
        return max(0.0, min(1.0, float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


class AnswerJudge:
    """LLM judge: scores an answer's faithfulness to context and relevance to the question."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def score(self, question: str, context: str, answer: str) -> GenerationScores:
        raw = await self._llm.generate(
            _JUDGE_PROMPT.format(question=question, context=context, answer=answer)
        )
        data = extract_json(raw)
        return GenerationScores(
            faithfulness=_clip01(data.get("faithfulness")),
            answer_relevance=_clip01(data.get("answer_relevance")),
        )
