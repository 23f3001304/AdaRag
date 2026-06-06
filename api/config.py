"""Config endpoint: read + edit the provider config (proxied to the host bridge)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from providers.http_bridge import bridge_get_config, bridge_put_config

router = APIRouter(tags=["config"])


class ConfigUpdate(BaseModel):
    llm_provider: str | None = None
    llm_model: str | None = None
    vision_provider: str | None = None
    vision_model: str | None = None
    ocr_provider: str | None = None
    claude_cli_path: str | None = None
    gemini_cli_path: str | None = None
    ollama_base_url: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    openrouter_api_key: str | None = None
    # The ingest ambiguity model is held API-side (live), not in the bridge .env.
    ambiguity_provider: str | None = None
    ambiguity_model: str | None = None


def _own_config(s) -> dict:
    fields = (
        "llm_provider",
        "llm_model",
        "vision_provider",
        "vision_model",
        "ocr_provider",
        "claude_cli_path",
        "gemini_cli_path",
        "ollama_base_url",
    )
    cfg = {f: getattr(s, f) for f in fields}
    cfg["keys"] = {
        n: bool(getattr(s, f"{n}_api_key")) for n in ("anthropic", "openai", "openrouter")
    }
    return cfg


@router.get("/config")
async def get_config(request: Request) -> dict:
    """The current provider config (read from the host bridge when forwarding to it)."""
    s = request.app.state.settings
    if s.llm_provider == "cli-bridge":
        cfg = await bridge_get_config(s.cli_bridge_url)
    else:
        cfg = _own_config(s)
    provider, model = request.app.state.buckets.ambiguity.get()
    cfg["ambiguity_provider"] = provider
    cfg["ambiguity_model"] = model
    return cfg


@router.put("/config")
async def put_config(request: Request, body: ConfigUpdate) -> dict:
    """Update the config; the ambiguity model is set API-side, the rest proxied to the bridge."""
    data = body.model_dump(exclude_none=True)
    amb_provider = data.pop("ambiguity_provider", None)
    amb_model = data.pop("ambiguity_model", None)
    if amb_provider is not None or amb_model is not None:
        request.app.state.buckets.ambiguity.set(amb_provider or "", amb_model or "")
    s = request.app.state.settings
    if s.llm_provider != "cli-bridge":
        return {"ok": False, "error": "editing config requires the cli-bridge deployment"}
    resp = await bridge_put_config(s.cli_bridge_url, data) if data else {"ok": True}
    # Round-trip the api-side ambiguity fields too so the frontend draft stays fully populated.
    provider, model = request.app.state.buckets.ambiguity.get()
    cfg = resp.get("config")
    if isinstance(cfg, dict):
        cfg["ambiguity_provider"] = provider
        cfg["ambiguity_model"] = model
    return resp
