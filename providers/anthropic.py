"""Anthropic provider: LLM generation via the Messages API."""

from __future__ import annotations

from anthropic import AsyncAnthropic

MAX_TOKENS = 1024


class AnthropicLLM:
    """LLMProvider backed by Anthropic Claude."""

    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self._client = AsyncAnthropic(api_key=api_key)

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        resp = await self._client.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            system=system or "",
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")
