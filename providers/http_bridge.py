"""HTTP bridge providers: delegate LLM/vision to a host-side CLI bridge over HTTP.

A Linux container can't exec the host's (Windows) CLI shims, so it calls a small HTTP server running
on the host (scripts/cli_bridge.py) where the Claude/Gemini CLIs are installed and logged in. Select
with ``llm_provider`` / ``vision_provider`` = "cli-bridge" and point ``cli_bridge_url`` at the host.
"""

from __future__ import annotations

import base64

import httpx

_TIMEOUT = 180.0  # CLI round-trips are slow (seconds); keep the HTTP client patient


class HttpBridgeLLM:
    """LLMProvider that proxies generate() to a host CLI bridge over HTTP."""

    def __init__(self, base_url: str, model: str = "") -> None:
        self.model = model
        self._url = base_url.rstrip("/")

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{self._url}/generate", json={"prompt": prompt, "system": system}
            )
            resp.raise_for_status()
            return resp.json()["text"]


class HttpBridgeVision:
    """VisionProvider that proxies describe() to a host CLI bridge over HTTP."""

    def __init__(self, base_url: str, model: str = "") -> None:
        self.model = model
        self._url = base_url.rstrip("/")

    async def describe(self, image: bytes, prompt: str) -> str:
        payload = {"image_b64": base64.b64encode(image).decode("ascii"), "prompt": prompt}
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(f"{self._url}/vision", json=payload)
            resp.raise_for_status()
            return resp.json()["text"]
