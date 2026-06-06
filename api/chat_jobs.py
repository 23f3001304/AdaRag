"""In-memory chat answer jobs so a refresh or a closed tab never loses an in-flight answer.

Generation runs as a background task that keeps filling the job regardless of any connection; an
SSE client (the original request or a reconnecting tab) just *observes* the job - replaying what is
buffered, then streaming the rest until done. Stop is an explicit signal that cancels the task.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass
class ChatJob:
    """One answer being generated: the buffered output plus the task producing it."""

    query: str = ""
    text: str = ""
    thinking: str = ""
    citations: list = field(default_factory=list)
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
        sent_text = sent_thinking = 0
        sent_query = False
        while True:
            if self.query and not sent_query:
                yield {"type": "query", "text": self.query}
                sent_query = True
            if len(self.thinking) > sent_thinking:
                yield {"type": "thinking", "text": self.thinking[sent_thinking:]}
                sent_thinking = len(self.thinking)
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
    """Registry of in-flight + recently finished jobs, keyed by a client-supplied message id."""

    def __init__(self, keep: int = 50) -> None:
        self._jobs: dict[str, ChatJob] = {}
        self._order: list[str] = []
        self._keep = keep

    def start(self, message_id: str, events: AsyncIterator[dict]) -> ChatJob:
        job = ChatJob()
        job.task = asyncio.create_task(job.run(events))
        self._jobs[message_id] = job
        self._order.append(message_id)
        while len(self._order) > self._keep:
            self._jobs.pop(self._order.pop(0), None)
        return job

    def get(self, message_id: str) -> ChatJob | None:
        return self._jobs.get(message_id)

    def stop(self, message_id: str) -> bool:
        job = self._jobs.get(message_id)
        if job and job.task and not job.task.done():
            job.task.cancel()
            return True
        return False
