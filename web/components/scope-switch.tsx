"use client";

import { cn } from "@/lib/cn";

export type Scope = "strict" | "medium" | "lazy";

const STEPS: { value: Scope; label: string; hint: string }[] = [
  { value: "strict", label: "strict", hint: "Answer only from the retrieved context." },
  { value: "medium", label: "medium", hint: "Prefer context; allow general knowledge when needed." },
  { value: "lazy", label: "lazy", hint: "Open - context, general knowledge, and tools all allowed." },
];

// Three-state pill segmented control. Strict on the left, lazy on the right.
export function ScopeSwitch({ value, onChange }: { value: Scope; onChange: (s: Scope) => void }) {
  return (
    <div className="flex items-center rounded-md border border-line bg-bg p-0.5">
      {STEPS.map((s) => (
        <button
          key={s.value}
          onClick={() => onChange(s.value)}
          title={s.hint}
          className={cn(
            "rounded px-2 py-0.5 text-[11px] transition-colors",
            value === s.value
              ? "bg-accent/15 text-accent"
              : "text-muted hover:text-fg",
          )}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}
