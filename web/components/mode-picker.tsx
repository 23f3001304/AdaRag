"use client";

import { Check, ChevronsUpDown, Cpu } from "lucide-react";
import { useState } from "react";

import type { ModeOption } from "@/lib/api";
import { cn } from "@/lib/cn";

const label = (m: ModeOption) => `${m.provider.replace("-cli", "")} · ${m.model}`;
const same = (a?: ModeOption, b?: ModeOption) => a?.provider === b?.provider && a?.model === b?.model;

// Per-chat model switcher: pick a detected provider+model, or the deployment default.
export function ModePicker({
  modes,
  value,
  onChange,
}: {
  modes: ModeOption[];
  value?: ModeOption;
  onChange: (m: ModeOption | undefined) => void;
}) {
  const [open, setOpen] = useState(false);
  const pick = (m: ModeOption | undefined) => {
    onChange(m);
    setOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 rounded-md border border-line bg-bg px-2.5 py-1.5 text-xs text-fg transition-colors hover:border-line-2"
      >
        <Cpu size={13} className={value ? "text-accent" : "text-faint"} />
        <span className="max-w-44 truncate font-mono">{value ? label(value) : "default model"}</span>
        <ChevronsUpDown size={12} className="text-faint" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 z-20 mt-1 max-h-72 w-60 overflow-y-auto rounded-md border border-line-2 bg-panel-2 p-1 shadow-2xl">
            <Row label="default model" active={!value} onClick={() => pick(undefined)} />
            {modes.map((m) => (
              <Row
                key={`${m.provider}:${m.model}`}
                label={label(m)}
                active={same(m, value)}
                onClick={() => pick(m)}
              />
            ))}
            {modes.length === 0 && (
              <p className="px-2 py-3 text-center text-[11px] text-faint">
                No models detected. Is the bridge running?
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function Row({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2 rounded px-2 py-1.5 text-left transition-colors",
        active ? "text-fg" : "text-muted hover:bg-panel hover:text-fg",
      )}
    >
      <span className="min-w-0 flex-1 truncate font-mono text-xs">{label}</span>
      {active && <Check size={13} className="shrink-0 text-accent" />}
    </button>
  );
}
