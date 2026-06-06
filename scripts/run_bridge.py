"""Launch the CLI bridge with the right event-loop policy on Windows.

The default Selector-based loop on Windows can't spawn subprocesses (the bridge runs the local
CLIs via asyncio.create_subprocess_exec, which raises NotImplementedError there). Setting the
Proactor policy before importing uvicorn fixes it. No --reload because it spawns a child process
that can't import the bridge module - restart with Ctrl+C and re-run when you change bridge code.

    uv run python scripts/run_bridge.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Make the project root importable so uvicorn finds `scripts.cli_bridge`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn  # noqa: E402 - must come after the policy + path are set

if __name__ == "__main__":
    uvicorn.run("scripts.cli_bridge:app", host="0.0.0.0", port=8088)
