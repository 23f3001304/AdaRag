"""Host-side CLI bridge: expose the local Claude/Gemini CLIs over HTTP so a container can use them.

A Dockerized API can't run the host's CLI shims, so run this on the HOST (where the CLIs are
installed + logged in) and point the container at it:

    uv run uvicorn scripts.cli_bridge:app --host 0.0.0.0 --port 8088      # on the host
    # container env: LLM_PROVIDER=cli-bridge  VISION_PROVIDER=cli-bridge
    #                CLI_BRIDGE_URL=http://host.docker.internal:8088

It reuses the app's own provider classes, proxying to whatever real CLI the host settings select
(llm_provider / vision_provider — must not be "cli-bridge" here, or it would call itself). Bind to
0.0.0.0 only on a trusted network: this endpoint runs your authenticated CLIs.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import get_settings  # noqa: E402
from providers.registry import build_llm, build_vision  # noqa: E402


class GenerateIn(BaseModel):
    prompt: str
    system: str | None = None


class VisionIn(BaseModel):
    image_b64: str
    prompt: str


_settings = get_settings()
_llm = build_llm(_settings)
_vision = build_vision(_settings)

app = FastAPI(title="AdaRag CLI bridge")


@app.get("/health")
async def health() -> dict:
    """Report readiness and which host CLIs back this bridge."""
    return {"status": "ok", "llm": _settings.llm_provider, "vision": _settings.vision_provider}


@app.post("/generate")
async def generate(body: GenerateIn) -> dict:
    """Proxy a text generation to the host LLM CLI."""
    return {"text": await _llm.generate(body.prompt, system=body.system)}


@app.post("/vision")
async def vision(body: VisionIn) -> dict:
    """Proxy an image description to the host vision CLI."""
    return {"text": await _vision.describe(base64.b64decode(body.image_b64), body.prompt)}
