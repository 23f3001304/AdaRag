"""Usage metering: accumulate LLM cost, tokens, and latency for cost-per-query / cost-per-MB.

A process-wide `METER` that providers record into; callers `reset()` before a unit of work and
`snapshot()` after, attributing cost + latency to it. This history is what the Phase 5 optimizer
needs to claim "-23% latency at equal relevance" rather than just "better quality".
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Usage:
    """Accumulated LLM usage: call count, USD cost, token counts, and wall-time."""

    calls: int = 0
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    ms: float = 0.0

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            self.calls + other.calls,
            self.cost_usd + other.cost_usd,
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
            self.ms + other.ms,
        )

    def line(self) -> str:
        """One-line human summary."""
        return (
            f"{self.calls} calls  ${self.cost_usd:.4f}  "
            f"{self.input_tokens}+{self.output_tokens} tok  {self.ms / 1000:.1f}s"
        )


class UsageMeter:
    """A running total of LLM usage: providers record in; callers snapshot/reset per unit."""

    def __init__(self) -> None:
        self._total = Usage()

    def record(
        self,
        *,
        cost_usd: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        ms: float = 0.0,
    ) -> None:
        self._total += Usage(1, cost_usd, input_tokens, output_tokens, ms)

    def snapshot(self) -> Usage:
        return self._total

    def reset(self) -> Usage:
        """Return the accumulated usage and start a fresh count."""
        prev = self._total
        self._total = Usage()
        return prev


METER = UsageMeter()
