"""Stdio MCP server that relays claude-cli permission prompts to the AdaRag bridge.

claude-cli is invoked with `--permission-prompt-tool mcp__adarag__permission_prompt`. When the
model wants to use a tool, claude-cli calls THIS server's `permission_prompt` tool. The handler
makes an HTTP POST to the bridge's /permission/ask endpoint, which:

  - registers a pending request keyed by id;
  - pushes a permission_required event to the active /stream session so the api/frontend can
    show the inline approve/deny card;
  - blocks (long-polls) until the user's decision arrives via POST /permission/{id}/decide.

The decision shape is what claude-cli expects from a permission-prompt tool result:
  {"behavior": "allow"} | {"behavior": "deny", "message": "..."}
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BRIDGE_URL = os.environ.get("ADARAG_BRIDGE_URL", "http://localhost:8088")
SESSION_ID = os.environ.get("ADARAG_SESSION_ID", "")
TIMEOUT = 600  # seconds the bridge will wait for the user


def _send(obj: dict) -> None:
    """Write one JSON-RPC line to stdout."""
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _initialize(req: dict) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req["id"],
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "adarag", "version": "0.1.0"},
        },
    }


def _tools_list(req: dict) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req["id"],
        "result": {
            "tools": [
                {
                    "name": "permission_prompt",
                    "description": "Ask the AdaRag user to approve or deny a tool use.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "tool_name": {"type": "string"},
                            "input": {"type": "object"},
                        },
                        "required": ["tool_name", "input"],
                    },
                }
            ],
        },
    }


def _tools_call(req: dict) -> dict:
    """Forward the permission request to the bridge; block until the user decides."""
    args = req.get("params", {}).get("arguments", {})
    payload = {
        "session_id": SESSION_ID,
        "tool_name": args.get("tool_name", ""),
        "input": args.get("input", {}),
    }
    try:
        data = urllib.request.Request(
            f"{BRIDGE_URL.rstrip('/')}/permission/ask",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(data, timeout=TIMEOUT) as resp:
            decision = json.loads(resp.read())
    except (urllib.error.URLError, OSError, ValueError) as exc:
        decision = {"behavior": "deny", "message": f"permission relay failed: {exc}"}
    return {
        "jsonrpc": "2.0",
        "id": req["id"],
        "result": {"content": [{"type": "text", "text": json.dumps(decision)}]},
    }


_HANDLERS = {"initialize": _initialize, "tools/list": _tools_list, "tools/call": _tools_call}


def main() -> None:
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = req.get("method")
        handler = _HANDLERS.get(method)
        if handler is None:
            if "id" in req:
                _send(
                    {
                        "jsonrpc": "2.0",
                        "id": req["id"],
                        "error": {"code": -32601, "message": f"method not found: {method}"},
                    }
                )
            continue
        try:
            _send(handler(req))
        except Exception as exc:  # noqa: BLE001 - JSON-RPC error response is the contract
            if "id" in req:
                _send(
                    {
                        "jsonrpc": "2.0",
                        "id": req["id"],
                        "error": {"code": -32603, "message": str(exc)},
                    }
                )


if __name__ == "__main__":
    main()
