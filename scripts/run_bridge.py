"""Launch the CLI bridge with the right event-loop policy on Windows.

uvicorn's --reload mode on Windows otherwise uses a Selector-based loop, and the bridge runs the
local CLIs as subprocesses (asyncio.create_subprocess_exec), which raises NotImplementedError on
that loop. Setting the Proactor policy BEFORE uvicorn imports fixes it.

    uv run python scripts/run_bridge.py
"""

from __future__ import annotations

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn  # noqa: E402 - must come after the policy is set

if __name__ == "__main__":
    uvicorn.run("scripts.cli_bridge:app", host="0.0.0.0", port=8088, reload=True)
