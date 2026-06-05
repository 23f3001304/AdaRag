"""HTTP bridge providers: delegate LLM/vision to a host-side CLI bridge over HTTP.

A Linux container can't exec the host's (Windows) CLI shims, so it calls a small HTTP server running
on the host (scripts/cli_bridge.py) where the Claude/Gemini CLIs are installed and logged in. Select
with ``llm_provider`` / ``vision_provider`` = "cli-bridge" and point ``cli_bridge_url`` at the host.
"""

from __future__ import annotations

import base64

import httpx

_TIMEOUT = 180.0  # CLI round-trips are slow (seconds); keep the HTTP client patient


async def bridge_models(base_url: str) -> list[dict]:
    """Ask a bridge which provider+model combos are available on its host."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{base_url.rstrip('/')}/models")
        resp.raise_for_status()
        return resp.json().get("modes", [])


async def bridge_get_config(base_url: str) -> dict:
    """Read the host config from a bridge (keys reported as set/unset only)."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{base_url.rstrip('/')}/config")
        resp.raise_for_status()
        return resp.json()


async def bridge_put_config(base_url: str, data: dict) -> dict:
    """Update the host config via a bridge (writes its .env + hot-reloads)."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.put(f"{base_url.rstrip('/')}/config", json=data)
        resp.raise_for_status()
        return resp.json()


class HttpBridgeLLM:
    """LLMProvider that proxies generate() to a host CLI bridge over HTTP.

    With a ``provider``, the bridge routes to that specific provider+model (chat model switching);
    without one it uses the bridge's default host LLM.
    """

    def __init__(self, base_url: str, model: str = "", provider: str = "") -> None:
        self.model = model
        self._provider = provider
        self._url = base_url.rstrip("/")

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        payload: dict = {"prompt": prompt, "system": system}
        if self._provider and self.model:
            payload["provider"] = self._provider
            payload["model"] = self.model
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(f"{self._url}/generate", json=payload)
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
