"""Bridge-side state and endpoints for permission bubbling (slice 2C).

The MCP stdio server (scripts/permission_mcp.py) calls /permission/ask for every tool the model
wants to use. We park a pending Future, push a permission_required event onto the active /stream
session's queue, and block until the user decides via /permission/{id}/decide.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["permission"])

# Module-level state - simple in-memory map. A bridge restart drops pending permissions, which
# is fine: claude-cli holds the MCP tool call open and times out; the chat reports a deny.
_pending: dict[str, dict] = {}
_session_queues: dict[str, asyncio.Queue] = {}


def session_queue(session_id: str) -> asyncio.Queue:
    """Get or create the permission event queue for a /stream session."""
    if session_id not in _session_queues:
        _session_queues[session_id] = asyncio.Queue()
    return _session_queues[session_id]


def release_session(session_id: str) -> None:
    """Drop the session's queue when its /stream finishes."""
    _session_queues.pop(session_id, None)


def _queue_for(session_id: str) -> asyncio.Queue | None:
    return _session_queues.get(session_id)


async def merge_with_queue(
    gen: AsyncIterator[dict], queue: asyncio.Queue | None
) -> AsyncIterator[dict]:
    """Yield LLM stream events interleaved with permission events from a session queue.

    Without a queue this is just the LLM stream. With one, we race a queue.get() task against the
    LLM stream task and yield whichever fires next, until the LLM stream completes.
    """
    if queue is None:
        async for ev in gen:
            yield ev
        return
    gen_iter = gen.__aiter__()
    gen_task = asyncio.create_task(gen_iter.__anext__())
    q_task = asyncio.create_task(queue.get())
    try:
        while True:
            done, _ = await asyncio.wait(
                {gen_task, q_task}, return_when=asyncio.FIRST_COMPLETED
            )
            if gen_task in done:
                try:
                    yield gen_task.result()
                except StopAsyncIteration:
                    break
                gen_task = asyncio.create_task(gen_iter.__anext__())
            if q_task in done:
                yield q_task.result()
                q_task = asyncio.create_task(queue.get())
    finally:
        gen_task.cancel()
        q_task.cancel()



class PermissionAskIn(BaseModel):
    session_id: str = ""
    tool_name: str
    input: dict = {}


class PermissionDecideIn(BaseModel):
    allow: bool
    message: str = ""


@router.post("/permission/ask")
async def permission_ask(body: PermissionAskIn) -> dict:
    """Park a permission request, emit the event upstream, block until the user decides."""
    rid = str(uuid.uuid4())
    future: asyncio.Future = asyncio.get_event_loop().create_future()
    _pending[rid] = {"future": future, "session_id": body.session_id}
    queue = _session_queues.get(body.session_id)
    if queue is not None:
        await queue.put(
            {
                "type": "permission_required",
                "id": rid,
                "tool_name": body.tool_name,
                "input": body.input,
            }
        )
    try:
        return await asyncio.wait_for(future, timeout=600)
    except (TimeoutError, asyncio.CancelledError):
        return {"behavior": "deny", "message": "permission request timed out or was cancelled"}
    finally:
        _pending.pop(rid, None)


@router.post("/permission/{rid}/decide")
async def permission_decide(rid: str, body: PermissionDecideIn) -> dict:
    """Set the decision for a parked permission request; unblocks the MCP server's long-poll."""
    entry = _pending.get(rid)
    if entry is None or entry["future"].done():
        return {"ok": False, "error": "not pending"}
    entry["future"].set_result(
        {"behavior": "allow" if body.allow else "deny", "message": body.message or ""}
    )
    return {"ok": True}
