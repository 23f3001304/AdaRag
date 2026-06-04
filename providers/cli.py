"""LLM providers that shell out to an authenticated local CLI (Claude Code, Gemini).

No API key needed — each CLI uses its own stored login (run `claude` / `gemini` once to log in).
A call spawns the CLI in headless mode (~seconds of startup), so these suit answer generation,
not high-volume per-chunk enrichment — keep Ollama for that.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import uuid
from pathlib import Path

from core.usage import METER

DEFAULT_TIMEOUT = 120.0


class CLIError(RuntimeError):
    """A CLI provider failed: missing binary, non-zero exit, timeout, or unparseable output."""


def _resolve(argv: list[str]) -> list[str]:
    """Resolve argv[0] to a real path; wrap Windows .cmd/.bat shims so they're executable."""
    exe = shutil.which(argv[0])
    if exe is None:
        raise CLIError(f"CLI not found: {argv[0]!r}. Install it or set its path in config.")
    if os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", exe, *argv[1:]]
    return [exe, *argv[1:]]


async def _run(argv: list[str], stdin_text: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Run argv with stdin_text on stdin and return stdout. Raises CLIError on any failure."""
    proc = await asyncio.create_subprocess_exec(
        *_resolve(argv),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(stdin_text.encode("utf-8")), timeout)
    except TimeoutError as exc:
        proc.kill()
        raise CLIError(f"{argv[0]} timed out after {timeout:.0f}s") from exc
    if proc.returncode != 0:
        detail = (err.decode("utf-8", "replace") or out.decode("utf-8", "replace")).strip()
        raise CLIError(f"{argv[0]} exited {proc.returncode}: {detail[:500]}")
    return out.decode("utf-8", "replace")


def _record_usage(data: dict) -> None:
    """Record a Claude CLI JSON result's cost/tokens/latency into the usage meter."""
    usage = data.get("usage", {})
    METER.record(
        cost_usd=float(data.get("total_cost_usd") or 0.0),
        input_tokens=int(usage.get("input_tokens") or 0),
        output_tokens=int(usage.get("output_tokens") or 0),
        ms=float(data.get("duration_ms") or 0.0),
    )


class ClaudeCodeLLM:
    """LLMProvider via the Claude Code CLI (`claude -p`); rides the CLI's own login, no key."""

    def __init__(self, model: str = "", binary: str = "claude") -> None:
        self.model = model
        self._binary = binary

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        text = f"{system}\n\n{prompt}" if system else prompt
        argv = [self._binary, "-p", "--output-format", "json"]
        if self.model:
            argv += ["--model", self.model]
        raw = await _run(argv, text)  # prompt on stdin (handles long RAG contexts)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CLIError(f"unexpected claude output: {raw[:300]!r}") from exc
        if data.get("is_error"):
            raise CLIError(f"claude: {data.get('result', 'error')}")
        _record_usage(data)
        return data["result"]


class GeminiCLILLM:
    """LLMProvider via the Gemini CLI (`gemini -p`); rides the CLI's own login, no key."""

    def __init__(self, model: str = "", binary: str = "gemini") -> None:
        self.model = model
        self._binary = binary

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        text = f"{system}\n\n{prompt}" if system else prompt
        # Gemini reads the prompt from stdin when no -p arg is given (avoids cmd arg-escaping).
        argv = [self._binary]
        if self.model:
            argv += ["-m", self.model]
        return (await _run(argv, text)).strip()


class ClaudeCliVision:
    """Vision via the Claude CLI: writes the image to a temp file it reads with an @reference."""

    def __init__(self, model: str = "", binary: str = "claude") -> None:
        self.model = model
        self._binary = binary

    async def describe(self, image: bytes, prompt: str) -> str:
        tmp = Path("data") / f"_vis_{uuid.uuid4().hex}.png"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(image)
        try:
            argv = [self._binary, "-p", "--output-format", "json"]
            if self.model:
                argv += ["--model", self.model]
            data = json.loads(await _run(argv, f"{prompt}\n\n@{tmp.as_posix()}"))
            if data.get("is_error"):
                raise CLIError(f"claude vision: {data.get('result', 'error')}")
            _record_usage(data)
            return data["result"]
        finally:
            tmp.unlink(missing_ok=True)
