"""Chat answer jobs so a refresh, closed tab, or server restart never loses an in-flight answer.

Generation runs as a background task that keeps filling the job regardless of any connection; an
SSE client (the original request or a reconnecting tab) just *observes* the job - replaying what is
buffered, then streaming the rest until done. On completion the buffer is saved to Postgres so a
restart can still serve `/chat/stream/{message_id}` by hydrating a job from the row.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from core.db import Database
from core.models import ChatJobRow

_SNAPSHOT_INTERVAL = 0.6  # seconds between mid-stream checkpoints to Postgres


@dataclass
class ChatJob:
    """One answer being generated: the buffered output plus the task producing it."""

    query: str = ""
    text: str = ""
    thinking: str = ""
    citations: list = field(default_factory=list)
    tools: list = field(default_factory=list)  # ordered tool_use / tool_result events (agent mode)
    status: str = "running"  # running | done | error
    error: str = ""
    task: asyncio.Task | None = None

    async def run(self, events: AsyncIterator[dict]) -> None:
        """Drive the job from a chat_stream() generator; survives the client disconnecting."""
        try:
            async for ev in events:
                kind = ev.get("type")
                if kind == "query":
                    self.query = ev.get("text", "")
                elif kind == "text":
                    self.text += ev.get("text", "")
                elif kind == "thinking":
                    self.thinking += ev.get("text", "")
                elif kind in ("tool_use", "tool_result", "permission_required"):
                    self.tools.append(ev)
                elif kind == "done":
                    self.citations = ev.get("citations", [])
                elif kind == "error":
                    self.error, self.status = ev.get("text", ""), "error"
            if self.status == "running":
                self.status = "done"
        except asyncio.CancelledError:
            self.status = "done"  # an explicit Stop keeps whatever was generated so far
            raise
        except Exception as exc:  # noqa: BLE001 - any failure becomes a surfaced error event
            self.error, self.status = str(exc), "error"

    async def observe(self) -> AsyncIterator[dict]:
        """Events for a (re)connecting client: replay the buffer, then stream new output to done."""
        sent_text = sent_thinking = sent_tools = 0
        sent_query = False
        while True:
            if self.query and not sent_query:
                yield {"type": "query", "text": self.query}
                sent_query = True
            if len(self.thinking) > sent_thinking:
                yield {"type": "thinking", "text": self.thinking[sent_thinking:]}
                sent_thinking = len(self.thinking)
            while sent_tools < len(self.tools):
                yield self.tools[sent_tools]
                sent_tools += 1
            if len(self.text) > sent_text:
                yield {"type": "text", "text": self.text[sent_text:]}
                sent_text = len(self.text)
            if self.status != "running":
                if self.status == "error":
                    yield {"type": "error", "text": self.error}
                yield {"type": "done", "citations": self.citations}
                return
            await asyncio.sleep(0.05)


class ChatJobs:
    """Registry of in-flight + recently finished jobs, keyed by a client-supplied message id.

    A completed job is also persisted to Postgres so a server restart can still replay it via
    `get()` (the in-memory map is empty on boot, but the row hydrates back into a finished job).
    """

    def __init__(self, db: Database, keep: int = 50) -> None:
        self._db = db
        self._jobs: dict[str, ChatJob] = {}
        self._order: list[str] = []
        self._keep = keep

    def start(self, message_id: str, events: AsyncIterator[dict]) -> ChatJob:
        job = ChatJob()
        job.task = asyncio.create_task(self._run_and_persist(message_id, job, events))
        self._jobs[message_id] = job
        self._order.append(message_id)
        while len(self._order) > self._keep:
            self._jobs.pop(self._order.pop(0), None)
        return job

    async def _run_and_persist(
        self, message_id: str, job: ChatJob, events: AsyncIterator[dict]
    ) -> None:
        """Drive the job + checkpoint mid-stream so even an api crash leaves the partial answer."""
        snap = asyncio.create_task(self._snapshot_loop(message_id, job))
        try:
            await job.run(events)
        finally:
            snap.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await snap
            await self._save(message_id, job)

    async def _snapshot_loop(self, message_id: str, job: ChatJob) -> None:
        """Save the buffer periodically while the job is still running."""
        while True:
            await asyncio.sleep(_SNAPSHOT_INTERVAL)
            if job.status == "running":
                await self._save(message_id, job)

    async def _save(self, message_id: str, job: ChatJob) -> None:
        """Upsert the completed job into Postgres (best effort - a save failure must not throw)."""
        try:
            async with self._db.session() as session:
                row = await session.get(ChatJobRow, message_id)
                payload = {
                    "status": job.status,
                    "query": job.query,
                    "text": job.text,
                    "thinking": job.thinking,
                    "citations_json": json.dumps(job.citations),
                    "error": job.error,
                }
                # Tool events ride alongside citations in the same JSON column so a restart
                # replays them in order. Older rows without this key fall back to [].
                payload["citations_json"] = json.dumps(
                    {"citations": job.citations, "tools": job.tools}
                )
                if row is None:
                    session.add(ChatJobRow(message_id=message_id, **payload))
                else:
                    for k, v in payload.items():
                        setattr(row, k, v)
                await session.commit()
        except Exception:  # noqa: BLE001 - persistence is a backstop, not the critical path
            return

    async def get(self, message_id: str) -> ChatJob | None:
        """Return the live job if known; otherwise hydrate one from a persisted row."""
        job = self._jobs.get(message_id)
        if job is not None:
            return job
        try:
            async with self._db.session() as session:
                row = await session.get(ChatJobRow, message_id)
        except Exception:  # noqa: BLE001
            return None
        if row is None:
            return None
        # status="running" in a row hydrated from disk means the api died mid-stream and the final
        # save never ran. Surface the partial buffer as an interrupted job so the client sees the
        # tokens that were generated and can decide whether to retry.
        interrupted = row.status == "running"
        status = "error" if interrupted else row.status
        error = "answer was interrupted by a server restart" if interrupted else row.error
        # citations_json was repurposed to hold both citations and tools (slice 2C). Bare list
        # for older rows; new rows store a dict.
        parsed = json.loads(row.citations_json or "[]")
        citations, tools = (parsed, []) if isinstance(parsed, list) else (
            parsed.get("citations") or [],
            parsed.get("tools") or [],
        )
        return ChatJob(
            query=row.query,
            text=row.text,
            thinking=row.thinking,
            citations=citations,
            tools=tools,
            status=status,
            error=error,
        )

    def stop(self, message_id: str) -> bool:
        job = self._jobs.get(message_id)
        if job and job.task and not job.task.done():
            job.task.cancel()
            return True
        return False
