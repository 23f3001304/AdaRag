"use client";

import { HelpCircle, X } from "lucide-react";
import { useState } from "react";

import { useClarifications } from "@/components/clarification-context";
import type { Clarification } from "@/lib/api";

// The pending "who/what is this file about?" questions, answered inline on the Ingest tab.
export function ClarificationPanel() {
  const { items, answer, dismiss } = useClarifications();
  if (items.length === 0) return null;
  return (
    <div className="flex flex-col gap-3">
      {items.map((c) => (
        <Card key={c.id} c={c} onAnswer={answer} onDismiss={dismiss} />
      ))}
    </div>
  );
}

function Card({
  c,
  onAnswer,
  onDismiss,
}: {
  c: Clarification;
  onAnswer: (id: string, entity: string) => Promise<void>;
  onDismiss: (id: string) => Promise<void>;
}) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (entity: string) => {
    if (!entity.trim() || busy) return;
    setBusy(true);
    try {
      await onAnswer(c.id, entity.trim());
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-lg border border-accent/40 bg-accent/[0.06] p-4">
      <div className="flex items-start gap-2.5">
        <HelpCircle size={16} className="mt-0.5 shrink-0 text-accent" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-fg">{c.question}</p>
          <p className="mt-0.5 font-mono text-[11px] text-faint">{c.source}</p>
        </div>
        <button
          onClick={() => onDismiss(c.id)}
          title="Dismiss"
          className="shrink-0 text-faint transition-colors hover:text-fg"
        >
          <X size={14} />
        </button>
      </div>
      {c.candidates.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {c.candidates.map((name) => (
            <button
              key={name}
              disabled={busy}
              onClick={() => submit(name)}
              className="rounded-full border border-line px-2.5 py-1 text-xs text-muted transition-colors hover:border-accent hover:text-fg disabled:opacity-50"
            >
              {name}
            </button>
          ))}
        </div>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(value);
        }}
        className="mt-2.5 flex gap-2"
      >
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={busy}
          placeholder="or type a name…"
          className="min-w-0 flex-1 rounded-md border border-line bg-bg px-3 py-1.5 text-sm text-fg outline-none transition-colors focus:border-accent"
        />
        <button
          type="submit"
          disabled={busy || !value.trim()}
          className="rounded-md bg-accent px-3.5 py-1.5 text-sm font-medium text-bg transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "Saving…" : "Answer"}
        </button>
      </form>
    </div>
  );
}
