"use client";

import { Boxes, Check, ChevronsUpDown } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { cn } from "@/lib/cn";
import type { Skill } from "@/lib/skills";

export function SkillPicker({
  skills,
  value,
  onChange,
}: {
  skills: Skill[];
  value?: string;
  onChange: (id: string | undefined) => void;
}) {
  const [open, setOpen] = useState(false);
  const active = skills.find((s) => s.id === value);

  const pick = (id: string | undefined) => {
    onChange(id);
    setOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 rounded-md border border-line bg-bg px-2.5 py-1.5 text-xs text-fg transition-colors hover:border-line-2"
      >
        <Boxes size={13} className={active ? "text-accent" : "text-faint"} />
        <span className="max-w-40 truncate">{active ? active.name : "No skill"}</span>
        <ChevronsUpDown size={12} className="text-faint" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 z-20 mt-1 w-60 rounded-md border border-line-2 bg-panel-2 p-1 shadow-2xl">
            <Row label="No skill" active={!value} onClick={() => pick(undefined)} />
            {skills.map((s) => (
              <Row
                key={s.id}
                label={s.name}
                hint={`${s.bucket} · top_k ${s.topK}`}
                active={s.id === value}
                onClick={() => pick(s.id)}
              />
            ))}
            <Link
              href="/skills"
              className="mt-1 block border-t border-line px-2 py-1.5 font-mono text-[10px] text-faint transition-colors hover:text-accent"
            >
              manage skills →
            </Link>
          </div>
        </>
      )}
    </div>
  );
}

function Row({
  label,
  hint,
  active,
  onClick,
}: {
  label: string;
  hint?: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm transition-colors",
        active ? "text-fg" : "text-muted hover:bg-panel hover:text-fg",
      )}
    >
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {hint && <span className="shrink-0 font-mono text-[10px] text-faint">{hint}</span>}
      {active && <Check size={13} className="shrink-0 text-accent" />}
    </button>
  );
}
