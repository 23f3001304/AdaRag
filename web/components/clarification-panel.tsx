"use client";

import { HelpCircle, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";

import { useClarifications } from "@/components/clarification-context";
import type { Clarification } from "@/lib/api";

// One question at a time with an N-of-M counter; the rest of the queue peeks behind as a stack -
// same shape as the corner notification center collapsed. Answering or dismissing advances.
export function ClarificationPanel() {
  const { items, answer, dismiss } = useClarifications();
  const [step, setStep] = useState(0);
  if (items.length === 0) return null;
  const idx = Math.min(step, items.length - 1);
  const total = items.length;
  const current = items[idx];
  const peek = items.slice(idx + 1, idx + 3); // up to 2 cards peek behind the active one

  const handleAnswer = async (entity: string) => {
    await answer(current.id, entity);
    // Items reshuffle when one answers (the list shrinks); keep step at the same index so the next
    // queued question slides into the same slot.
    setStep((s) => Math.min(s, total - 2));
  };
  const handleDismiss = async () => {
    await dismiss(current.id);
    setStep((s) => Math.min(s, total - 2));
  };

  return (
    <div className="relative" style={{ minHeight: 168 + Math.min(peek.length, 2) * 9 }}>
      <AnimatePresence initial={false}>
        {peek.map((p, i) => (
          <motion.div
            key={p.id}
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1 - (i + 1) * 0.22, y: -(i + 1) * 9, scale: 1 - (i + 1) * 0.025 }}
            exit={{ opacity: 0 }}
            transition={{ type: "spring", stiffness: 420, damping: 34 }}
            style={{ zIndex: 1 + (peek.length - i) }}
            className="pointer-events-none absolute inset-x-0 top-0"
          >
            <Shell />
          </motion.div>
        ))}
        <motion.div
          key={current.id}
          initial={{ opacity: 0, y: 12, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -12, scale: 0.96 }}
          transition={{ type: "spring", stiffness: 420, damping: 34 }}
          style={{ zIndex: 10 }}
          className="absolute inset-x-0 top-0"
        >
          <ActiveCard
            c={current}
            counter={total > 1 ? `${idx + 1} / ${total}` : undefined}
            onAnswer={handleAnswer}
            onDismiss={handleDismiss}
          />
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

// An empty card that just provides the same outline + shadow for the peeking stack behind.
function Shell() {
  return <div className="h-[150px] rounded-xl border border-line bg-panel shadow-[0_8px_24px_-12px_rgba(0,0,0,0.55)]" />;
}

function ActiveCard({
  c,
  counter,
  onAnswer,
  onDismiss,
}: {
  c: Clarification;
  counter: string | undefined;
  onAnswer: (entity: string) => Promise<void>;
  onDismiss: () => Promise<void>;
}) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (entity: string) => {
    if (!entity.trim() || busy) return;
    setBusy(true);
    try {
      await onAnswer(entity.trim());
      setValue("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-xl border border-line bg-panel p-4 shadow-[0_12px_32px_-12px_rgba(0,0,0,0.65)]">
      <div className="flex items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-accent/15 text-accent">
          <HelpCircle size={16} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            {counter && (
              <span className="rounded-full border border-line-2 px-1.5 py-px font-mono text-[10px] tabular-nums text-muted">
                {counter}
              </span>
            )}
            <p className="min-w-0 truncate text-sm font-semibold text-fg">{c.question}</p>
          </div>
          <p className="mt-0.5 font-mono text-[11px] text-faint">{c.source}</p>
        </div>
        <button
          onClick={onDismiss}
          title="Skip"
          disabled={busy}
          className="shrink-0 text-faint transition-colors hover:text-fg disabled:opacity-50"
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
