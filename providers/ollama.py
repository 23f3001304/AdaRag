"""Ollama provider: local LLM generation + vision via a running Ollama server."""

from __future__ import annotations

import base64

from ollama import AsyncClient


class OllamaLLM:
    """LLMProvider backed by a local Ollama server (no API key)."""

    def __init__(self, base_url: str, model: str) -> None:
        self.model = model
        self._client = AsyncClient(host=base_url)

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        # think=False stops reasoning models (e.g. qwen3) from emitting <think> tokens.
        resp = await self._client.generate(
            model=self.model, prompt=prompt, system=system or "", think=False
        )
        return resp["response"]

    async def generate_thinking(self, prompt: str, *, system: str | None = None) -> tuple[str, str]:
        """Generate with reasoning on (qwen3-style); returns (answer, thinking)."""
        resp = await self._client.generate(
            model=self.model, prompt=prompt, system=system or "", think=True
        )
        return resp["response"], resp.get("thinking") or ""

    async def stream(self, prompt: str, *, system: str | None = None):
        """Yield {type: text|thinking, text} deltas from a streaming ollama generation."""
        async for chunk in await self._client.generate(
            model=self.model, prompt=prompt, system=system or "", think=True, stream=True
        ):
            think = chunk.get("thinking")
            if think:
                yield {"type": "thinking", "text": think}
            text = chunk.get("response")
            if text:
                yield {"type": "text", "text": text}


class OllamaVision:
    """VisionProvider backed by a local Ollama multimodal model (e.g. qwen2.5vl, llava, moondream).

    The model must be a vision model pulled into Ollama (`ollama pull qwen2.5vl`); a text-only model
    will ignore the image. Runs locally on the GPU — no API key, no per-call cost.
    """

    def __init__(self, base_url: str, model: str) -> None:
        self.model = model
        self._client = AsyncClient(host=base_url)

    async def describe(self, image: bytes, prompt: str) -> str:
        resp = await self._client.generate(
            model=self.model, prompt=prompt, images=[base64.b64encode(image).decode("ascii")]
        )
        return resp["response"]
