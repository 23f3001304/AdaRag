"""Host-side CLI bridge: expose the local Claude/Gemini CLIs over HTTP so a container can use them.

A Dockerized API can't run the host's CLI shims, so run this on the HOST (where the CLIs are
installed + logged in) and point the container at it:

    uv run uvicorn scripts.cli_bridge:app --host 0.0.0.0 --port 8088      # on the host
    # container env: LLM_PROVIDER=cli-bridge  VISION_PROVIDER=cli-bridge
    #                CLI_BRIDGE_URL=http://host.docker.internal:8088

It reuses the app's own provider classes, proxying to whatever real CLI the host settings select
(llm_provider / vision_provider — must not be "cli-bridge" here, or it would call itself). /generate
can route per request to any installed provider+model (chat model switching), /models reports
what is available, and /config reads + writes the host .env (the Settings page). Bind to 0.0.0.0
only on a trusted network: this runs your authenticated CLIs and can edit your .env.
"""

from __future__ import annotations

import base64
import re
import shutil
import sys
from pathlib import Path

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import Settings, get_settings  # noqa: E402
from providers.registry import build_llm, build_vision  # noqa: E402

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

# Editable host settings (field -> .env var). Secrets are write-only (never returned).
_EDITABLE = {
    "llm_provider": "LLM_PROVIDER",
    "llm_model": "LLM_MODEL",
    "vision_provider": "VISION_PROVIDER",
    "vision_model": "VISION_MODEL",
    "ocr_provider": "OCR_PROVIDER",
    "claude_cli_path": "CLAUDE_CLI_PATH",
    "gemini_cli_path": "GEMINI_CLI_PATH",
    "ollama_base_url": "OLLAMA_BASE_URL",
}
_SECRETS = {
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "openai_api_key": "OPENAI_API_KEY",
    "openrouter_api_key": "OPENROUTER_API_KEY",
}


class _State:
    """The bridge's live providers, rebuilt from the host settings when the .env changes."""

    def __init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        get_settings.cache_clear()
        self.settings: Settings = get_settings()
        self.llm = build_llm(self.settings)
        self.vision = build_vision(self.settings)
        self.llm_cache: dict[tuple[str, str], object] = {}


_state = _State()


class GenerateIn(BaseModel):
    prompt: str
    system: str | None = None
    provider: str | None = None  # optional per-request override (chat model switching)
    model: str | None = None
    thinking: bool = False  # ask reasoning models (ollama qwen3) to return their thinking


class VisionIn(BaseModel):
    image_b64: str
    prompt: str


class ConfigIn(BaseModel):
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


def _llm_for(provider: str, model: str):
    """Build (and cache) an LLM for a specific provider+model on the host."""
    key = (provider, model)
    if key not in _state.llm_cache:
        override = _state.settings.model_copy(update={"llm_provider": provider, "llm_model": model})
        _state.llm_cache[key] = build_llm(override)
    return _state.llm_cache[key]


def _detect_modes() -> list[dict]:
    """Report provider+model combos that are actually usable on this host (best-effort)."""
    s = _state.settings
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


def _read_config() -> dict:
    """Current host config; API keys are reported only as set/unset, never by value."""
    s = _state.settings
    cfg = {field: getattr(s, field) for field in _EDITABLE}
    cfg["keys"] = {
        name: bool(getattr(s, f"{name}_api_key")) for name in ("anthropic", "openai", "openrouter")
    }
    return cfg


def _write_env(updates: dict[str, str]) -> None:
    """Merge KEY=value updates into the .env file (create if missing), preserving other lines."""
    lines = _ENV_FILE.read_text(encoding="utf-8").splitlines() if _ENV_FILE.exists() else []
    out: list[str] = []
    seen: set[str] = set()
    for line in lines:
        match = re.match(r"\s*([A-Z_][A-Z0-9_]*)\s*=", line)
        if match and match.group(1) in updates:
            out.append(f"{match.group(1)}={updates[match.group(1)]}")
            seen.add(match.group(1))
        else:
            out.append(line)
    out += [f"{k}={v}" for k, v in updates.items() if k not in seen]
    _ENV_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")


app = FastAPI(title="AdaRag CLI bridge")


@app.get("/health")
async def health() -> dict:
    """Report readiness and which host CLIs back this bridge."""
    s = _state.settings
    return {"status": "ok", "llm": s.llm_provider, "vision": s.vision_provider}


@app.get("/models")
async def models() -> dict:
    """List provider+model combos available on the host (for the chat model switcher)."""
    return {"modes": _detect_modes()}


@app.get("/config")
async def get_config() -> dict:
    """The current host config (API keys reported as set/unset only)."""
    return _read_config()


@app.put("/config")
async def put_config(body: ConfigIn) -> dict:
    """Update the host .env and hot-reload the providers (a blank secret leaves it unchanged)."""
    data = body.model_dump(exclude_none=True)
    if data.get("llm_provider") == "cli-bridge" or data.get("vision_provider") == "cli-bridge":
        return {"ok": False, "error": "the bridge's own provider cannot be cli-bridge"}
    updates: dict[str, str] = {}
    for field, env in {**_EDITABLE, **_SECRETS}.items():
        if field in data and data[field] != "":
            updates[env] = str(data[field])
    if updates:
        _write_env(updates)
    try:
        _state.reload()
    except Exception as exc:  # bad provider name etc. — keep serving, report the failure
        return {"ok": False, "error": str(exc), "config": _read_config()}
    return {"ok": True, "config": _read_config()}


@app.post("/generate")
async def generate(body: GenerateIn) -> dict:
    """Proxy a text generation to the host LLM CLI, optionally to a chosen provider+model."""
    llm = _llm_for(body.provider, body.model) if body.provider and body.model else _state.llm
    if body.thinking and hasattr(llm, "generate_thinking"):
        text, thinking = await llm.generate_thinking(body.prompt, system=body.system)
        return {"text": text, "thinking": thinking}
    return {"text": await llm.generate(body.prompt, system=body.system)}


@app.post("/vision")
async def vision(body: VisionIn) -> dict:
    """Proxy an image description to the host vision CLI."""
    return {"text": await _state.vision.describe(base64.b64decode(body.image_b64), body.prompt)}
