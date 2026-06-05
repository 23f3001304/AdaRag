"use client";

import { Check, ChevronsUpDown, Database, Plus } from "lucide-react";
import { useState } from "react";

import { useBucket } from "@/components/bucket-context";
import { cn } from "@/lib/cn";

export function BucketSwitcher({ collapsed }: { collapsed: boolean }) {
  const { bucket, setBucket, buckets, create } = useBucket();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const n = name.trim();
    if (!n || busy) return;
    setBusy(true);
    try {
      await create(n);
      setName("");
      setOpen(false);
    } catch {
      /* surfaced elsewhere; keep the menu open */
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        title={collapsed ? `bucket: ${bucket}` : undefined}
        className={cn(
          "flex w-full items-center gap-2.5 rounded-md border border-line bg-panel py-2 text-left transition-colors hover:border-line-2",
          collapsed ? "justify-center px-0" : "px-2.5",
        )}
      >
        <Database size={15} className="shrink-0 text-accent" />
        {!collapsed && (
          <>
            <span className="flex min-w-0 flex-col leading-tight">
              <span className="font-mono text-[9px] uppercase tracking-wider text-faint">bucket</span>
              <span className="truncate text-sm text-fg">{bucket}</span>
            </span>
            <ChevronsUpDown size={14} className="ml-auto shrink-0 text-faint" />
          </>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div
            className={cn(
              "absolute z-20 mt-1 rounded-md border border-line-2 bg-panel-2 p-1 shadow-2xl",
              collapsed ? "left-0 w-48" : "inset-x-0",
            )}
          >
            <div className="max-h-52 overflow-y-auto">
              {buckets.map((b) => (
                <button
                  key={b}
                  onClick={() => {
                    setBucket(b);
                    setOpen(false);
                  }}
                  className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm text-muted transition-colors hover:bg-panel hover:text-fg"
                >
                  <span className="truncate">{b}</span>
                  {b === bucket && <Check size={14} className="ml-auto shrink-0 text-accent" />}
                </button>
              ))}
            </div>
            <div className="mt-1 flex items-center gap-1 border-t border-line px-1 pt-1.5">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submit()}
                placeholder="new bucket…"
                className="min-w-0 flex-1 bg-transparent px-1 py-1 text-sm text-fg outline-none placeholder:text-faint"
              />
              <button
                onClick={submit}
                disabled={busy}
                className="rounded p-1 text-faint transition-colors hover:bg-panel hover:text-accent disabled:opacity-40"
              >
                <Plus size={14} />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
