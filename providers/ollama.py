"""Ollama provider: local LLM generation via a running Ollama server."""

from __future__ import annotations

from ollama import AsyncClient


class OllamaLLM:
    """LLMProvider backed by a local Ollama server (no API key)."""

    def __init__(self, base_url: str, model: str) -> None:
        self.model = model
        self._client = AsyncClient(host=base_url)

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        resp = await self._client.generate(model=self.model, prompt=prompt, system=system or "")
        return resp["response"]
