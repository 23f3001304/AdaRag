"""Parsers that turn each CLI's stream-json line into our common UI delta shape.

Both claude-cli and gemini-cli expose `--output-format stream-json` but the event vocabularies
differ. This module flattens both into `{type: text|thinking|tool_use|tool_result, ...}` events
so the rest of the stack (chat orchestrator, SSE, chat_jobs, frontend ToolCard) is provider-
agnostic.
"""

from __future__ import annotations


def parse_claude_event(ev: dict):
    """One claude-cli stream-json line -> UI delta events.

    text/thinking come from stream_event.content_block_delta. Tool use is read from the assembled
    assistant message (it carries the complete input); tool_result is from the user message that
    follows. The stream_event start/delta for tool_use are skipped - they only have partial input.
    """
    msg_type = ev.get("type")
    if msg_type == "stream_event":
        event = ev.get("event", {})
        if event.get("type") == "content_block_delta":
            delta = event.get("delta", {})
            if delta.get("type") == "text_delta" and delta.get("text"):
                yield {"type": "text", "text": delta["text"]}
            elif delta.get("type") == "thinking_delta" and delta.get("thinking"):
                yield {"type": "thinking", "text": delta["thinking"]}
        return
    if msg_type not in ("assistant", "user"):
        return
    content = (ev.get("message") or {}).get("content") or []
    for block in content:
        kind = block.get("type")
        if kind == "tool_use":
            yield {
                "type": "tool_use",
                "id": block.get("id", ""),
                "name": block.get("name", ""),
                "input": block.get("input", {}),
            }
        elif kind == "tool_result":
            raw = block.get("content")
            text = raw if isinstance(raw, str) else (raw[0].get("text", "") if raw else "")
            yield {
                "type": "tool_result",
                "id": block.get("tool_use_id", ""),
                "text": text,
                "is_error": bool(block.get("is_error")),
            }


def parse_gemini_event(ev: dict):
    """One gemini-cli stream-json line -> UI delta events.

    Gemini's format is flatter than claude's: top-level `type` is one of init / message / tool_use
    / tool_result / result. Only assistant `message` events and tool_use/tool_result map to UI
    deltas; the rest are session metadata we drop.
    """
    kind = ev.get("type")
    if kind == "message" and ev.get("role") == "assistant":
        content = ev.get("content")
        if isinstance(content, str) and content:
            yield {"type": "text", "text": content}
        return
    if kind == "tool_use":
        yield {
            "type": "tool_use",
            "id": ev.get("tool_id", ""),
            "name": ev.get("tool_name", ""),
            "input": ev.get("parameters") or {},
        }
        return
    if kind == "tool_result":
        yield {
            "type": "tool_result",
            "id": ev.get("tool_id", ""),
            "text": ev.get("output", "") or ev.get("error", ""),
            "is_error": ev.get("status") not in ("success", None),
        }
