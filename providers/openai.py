"""OpenAI provider: LLM generation via the Chat Completions API."""

from __future__ import annotations

from openai import AsyncOpenAI


class OpenAILLM:
    """LLMProvider backed by OpenAI, or any OpenAI-compatible endpoint (e.g. OpenRouter)."""

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = await self._client.chat.completions.create(model=self.model, messages=messages)
        return resp.choices[0].message.content or ""
