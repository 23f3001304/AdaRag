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
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from core.usage import METER
from providers.cli_stream import parse_claude_event, parse_gemini_event

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


async def _stream_lines(argv: list[str], stdin_text: str, env: dict | None = None):
    """Run argv and yield its stdout line by line; kills the process if the consumer stops early."""
    proc = await asyncio.create_subprocess_exec(
        *_resolve(argv),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        env=env,
    )
    try:
        if proc.stdin:
            proc.stdin.write(stdin_text.encode("utf-8"))
            await proc.stdin.drain()
            proc.stdin.close()
        assert proc.stdout
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            yield line.decode("utf-8", "replace")
    finally:  # consumer cancelled (e.g. user hit Stop) -> terminate the CLI
        if proc.returncode is None:
            proc.kill()
        await proc.wait()


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

    async def stream(
        self,
        prompt: str,
        *,
        system: str | None = None,
        agent: bool = False,
        session_id: str = "",
    ):
        """Yield deltas from claude-cli; agent=True routes tool use through MCP permission prompts.

        In agent mode each tool call goes through `--permission-prompt-tool` which our stdio MCP
        server (scripts/permission_mcp.py) handles - the bridge bubbles the request to the user
        and only releases it back to claude once Approve is clicked. session_id correlates the
        MCP call back to this exact /stream subscription.
        """
        text = f"{system}\n\n{prompt}" if system else prompt
        argv = [self._binary, "-p", "--output-format", "stream-json", "--verbose"]
        argv += ["--include-partial-messages"]
        if self.model:
            argv += ["--model", self.model]
        env = None
        if agent:
            # claude-cli 2.1.x has no --permission-prompt-tool; --allowed-tools is the only way to
            # enable tool use in -p mode. Cards in the UI provide visibility; pre-approval would
            # need claude-cli to add a plug-in permission gate (it currently doesn't).
            argv += ["--allowed-tools", "Read Glob Grep Bash Edit Write"]
            env = {**os.environ, "ADARAG_SESSION_ID": session_id}
        async for raw in _stream_lines(argv, text, env=env):
            raw = raw.strip()
            if not raw:
                continue
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                continue
            for parsed in parse_claude_event(ev):
                yield parsed


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

    async def stream(
        self,
        prompt: str,
        *,
        system: str | None = None,
        agent: bool = False,
        session_id: str = "",  # noqa: ARG002 - kept for signature parity with claude-cli
    ):
        """Yield text + tool deltas from gemini-cli's --output-format stream-json.

        agent=True passes --yolo so the CLI auto-approves its tool calls (run_shell_command,
        read_file, edit_file, etc.) - visibility only, same trade-off as claude-cli.
        """
        text = f"{system}\n\n{prompt}" if system else prompt
        argv = [self._binary, "-p", text, "--output-format", "stream-json"]
        if self.model:
            argv += ["-m", self.model]
        if agent:
            argv += ["--yolo"]
        # gemini-cli takes the prompt via -p, so its stdin can be empty.
        async for raw in _stream_lines(argv, ""):
            raw = raw.strip()
            if not raw or not raw.startswith("{"):
                continue
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                continue
            for parsed in parse_gemini_event(ev):
                yield parsed


@contextmanager
def _temp_image(image: bytes) -> Iterator[Path]:
    """Write image bytes to a temp PNG the Claude CLI can @-reference, removed afterwards."""
    tmp = Path("data") / f"_vis_{uuid.uuid4().hex}.png"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(image)
    try:
        yield tmp
    finally:
        tmp.unlink(missing_ok=True)


@contextmanager
def _temp_image_dir(image: bytes) -> Iterator[Path]:
    """Write image bytes to a PNG in a throwaway dir OUTSIDE the repo, removed afterwards.

    Gemini's @-references honor .gitignore and are confined to the workspace, so (unlike Claude)
    its temp image can't live under the gitignored data/; it gets its own dir added via
    --include-directories.
    """
    folder = Path(tempfile.mkdtemp(prefix="adarag_vis_"))
    tmp = folder / "image.png"
    tmp.write_bytes(image)
    try:
        yield tmp
    finally:
        shutil.rmtree(folder, ignore_errors=True)


class ClaudeCliVision:
    """Vision via the Claude CLI: writes the image to a temp file it reads with an @reference."""

    def __init__(self, model: str = "", binary: str = "claude") -> None:
        self.model = model
        self._binary = binary

    async def describe(self, image: bytes, prompt: str) -> str:
        argv = [self._binary, "-p", "--output-format", "json"]
        if self.model:
            argv += ["--model", self.model]
        with _temp_image(image) as tmp:
            raw = await _run(argv, f"{prompt}\n\n@{tmp.as_posix()}")
        data = json.loads(raw)
        if data.get("is_error"):
            raise CLIError(f"claude vision: {data.get('result', 'error')}")
        _record_usage(data)
        return data["result"]


class GeminiCliVision:
    """Vision via the Gemini CLI: the @-referenced image goes in the -p prompt (not stdin), and
    its directory is added to the workspace so Gemini's gitignore-aware file tool can read it."""

    def __init__(self, model: str = "", binary: str = "gemini") -> None:
        self.model = model
        self._binary = binary

    async def describe(self, image: bytes, prompt: str) -> str:
        with _temp_image_dir(image) as tmp:
            argv = [self._binary]
            if self.model:
                argv += ["-m", self.model]
            argv += ["--include-directories", str(tmp.parent), "-p", f"{prompt} @{tmp.as_posix()}"]
            return (await _run(argv, "")).strip()
