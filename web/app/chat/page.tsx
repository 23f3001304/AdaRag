"use client";

import { CornerDownLeft, User } from "lucide-react";
import { useRef, useState } from "react";

import { Logo } from "@/components/logo";
import { Button } from "@/components/ui";
import { type Citation, api } from "@/lib/api";

interface Turn {
  role: "user" | "assistant";
  text: string;
  query?: string;
  citations?: Citation[];
}

export default function ChatPage() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const session = useRef("");
  if (!session.current) session.current = crypto.randomUUID();

  const send = async () => {
    const text = msg.trim();
    if (!text || busy) return;
    setMsg("");
    setTurns((t) => [...t, { role: "user", text }]);
    setBusy(true);
    try {
      const r = await api.chat(session.current, text, "default");
      setTurns((t) => [
        ...t,
        { role: "assistant", text: r.answer, query: r.search_query, citations: r.citations },
      ]);
    } catch (e) {
      const offline = String(e).includes("Failed to fetch");
      setTurns((t) => [
        ...t,
        { role: "assistant", text: offline ? "backend offline." : "request failed." },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-7rem)] max-w-3xl flex-col">
      <div className="mb-4">
        <h2 className="font-display text-2xl font-bold tracking-tight text-fg">Chat</h2>
        <p className="mt-1.5 text-sm text-muted">
          Multi-turn over the bucket. Follow-ups are rewritten to standalone queries before retrieval.
        </p>
      </div>

      <div className="flex flex-1 flex-col gap-5 overflow-y-auto pb-4">
        {turns.length === 0 && (
          <p className="mt-16 text-center text-sm text-faint">Ask something to start.</p>
        )}
        {turns.map((t, i) => (
          <TurnView key={i} turn={t} />
        ))}
        {busy && <p className="pl-9 text-sm text-faint">thinking…</p>}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
        className="flex gap-2 border-t border-line pt-4"
      >
        <input
          value={msg}
          onChange={(e) => setMsg(e.target.value)}
          placeholder="ask a question…"
          className="flex-1 rounded-md border border-line bg-panel px-3 py-2.5 text-sm text-fg outline-none placeholder:text-faint focus:border-line-2"
        />
        <Button type="submit" disabled={busy}>
          <CornerDownLeft size={14} /> Send
        </Button>
      </form>
    </div>
  );
}

function TurnView({ turn }: { turn: Turn }) {
  const isUser = turn.role === "user";
  const sources = [...new Set((turn.citations ?? []).map((c) => c.source))].slice(0, 5);
  return (
    <div className="flex gap-3">
      <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-md border border-line bg-panel">
        {isUser ? <User size={13} className="text-muted" /> : <Logo size={13} />}
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        {turn.query && (
          <span className="font-mono text-[10px] text-faint">searched: {turn.query}</span>
        )}
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-fg">{turn.text}</p>
        {sources.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1.5">
            {sources.map((s) => (
              <span
                key={s}
                className="truncate rounded border border-line px-1.5 py-px font-mono text-[10px] text-muted"
              >
                {s}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
