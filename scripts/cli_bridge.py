"""Host-side CLI bridge: expose the local Claude/Gemini CLIs over HTTP so a container can use them.

A Dockerized API can't run the host's CLI shims, so run this on the HOST (where the CLIs are
installed + logged in) and point the container at it:

    uv run uvicorn scripts.cli_bridge:app --host 0.0.0.0 --port 8088      # on the host
    # container env: LLM_PROVIDER=cli-bridge  VISION_PROVIDER=cli-bridge
    #                CLI_BRIDGE_URL=http://host.docker.internal:8088

It reuses the app's own provider classes, proxying to whatever real CLI the host settings select
(llm_provider / vision_provider — must not be "cli-bridge" here, or it would call itself). /generate
can route per request to any installed provider+model (chat model switching), and /models reports
what is available on the host. Bind to 0.0.0.0 only on a trusted network: this runs your CLIs.
"""

from __future__ import annotations

import base64
import shutil
import sys
from pathlib import Path

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import get_settings  # noqa: E402
from providers.registry import build_llm, build_vision  # noqa: E402


class GenerateIn(BaseModel):
    prompt: str
    system: str | None = None
    provider: str | None = None  # optional per-request override (chat model switching)
    model: str | None = None


class VisionIn(BaseModel):
    image_b64: str
    prompt: str


_settings = get_settings()
_llm = build_llm(_settings)
_vision = build_vision(_settings)
_llm_cache: dict[tuple[str, str], object] = {}


def _llm_for(provider: str, model: str):
    """Build (and cache) an LLM for a specific provider+model on the host."""
    key = (provider, model)
    if key not in _llm_cache:
        override = _settings.model_copy(update={"llm_provider": provider, "llm_model": model})
        _llm_cache[key] = build_llm(override)
    return _llm_cache[key]


def _detect_modes() -> list[dict]:
    """Report provider+model combos that are actually usable on this host (best-effort)."""
    s = _settings
    modes: list[dict] = []
    if shutil.which(s.claude_cli_path) or Path(s.claude_cli_path).exists():
        modes += [{"provider": "claude-cli", "model": m} for m in ("sonnet", "opus", "haiku")]
    if shutil.which(s.gemini_cli_path) or Path(s.gemini_cli_path).exists():
        modes += [
            {"provider": "gemini-cli", "model": m}
            for m in ("gemini-2.5-flash", "gemini-2.5-pro")
        ]
    try:
        resp = httpx.get(f"{s.ollama_base_url}/api/tags", timeout=2.0)
        for m in resp.json().get("models", []):
            name = m.get("name") or m.get("model")
            if name:
                modes.append({"provider": "ollama", "model": name})
    except Exception:
        pass
    if s.anthropic_api_key:
        modes.append({"provider": "anthropic", "model": s.llm_model or "claude-3-5-sonnet-latest"})
    if s.openai_api_key:
        modes.append({"provider": "openai", "model": "gpt-4o"})
    if s.openrouter_api_key:
        modes.append({"provider": "openrouter", "model": "anthropic/claude-3.5-sonnet"})
    return modes


app = FastAPI(title="AdaRag CLI bridge")


@app.get("/health")
async def health() -> dict:
    """Report readiness and which host CLIs back this bridge."""
    return {"status": "ok", "llm": _settings.llm_provider, "vision": _settings.vision_provider}


@app.get("/models")
async def models() -> dict:
    """List provider+model combos available on the host (for the chat model switcher)."""
    return {"modes": _detect_modes()}


@app.post("/generate")
async def generate(body: GenerateIn) -> dict:
    """Proxy a text generation to the host LLM CLI, optionally to a chosen provider+model."""
    llm = _llm_for(body.provider, body.model) if body.provider and body.model else _llm
    return {"text": await llm.generate(body.prompt, system=body.system)}


@app.post("/vision")
async def vision(body: VisionIn) -> dict:
    """Proxy an image description to the host vision CLI."""
    return {"text": await _vision.describe(base64.b64decode(body.image_b64), body.prompt)}
