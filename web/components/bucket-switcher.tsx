"use client";

import { Check, ChevronsUpDown, Database, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { useBucket } from "@/components/bucket-context";
import { Modal } from "@/components/modal";
import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";

export function BucketSwitcher({ collapsed }: { collapsed: boolean }) {
  const { bucket, setBucket, buckets, create, remove } = useBucket();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState<string | null>(null);
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);

  const submit = async () => {
    const n = name.trim();
    if (!n || busy) return;
    setBusy(true);
    try {
      await create(n);
      setName("");
      setOpen(false);
    } catch {
      /* keep the menu open on failure */
    } finally {
      setBusy(false);
    }
  };

  const doDelete = async () => {
    if (!confirm || confirmText !== confirm || deleting) return;
    setDeleting(true);
    try {
      await remove(confirm);
      setConfirm(null);
      setConfirmText("");
    } catch {
      /* keep the modal open on failure */
    } finally {
      setDeleting(false);
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
              collapsed ? "left-0 w-52" : "inset-x-0",
            )}
          >
            <div className="max-h-52 overflow-y-auto">
              {buckets.map((b) => (
                <div
                  key={b}
                  className={cn(
                    "group flex items-center gap-2 rounded px-2 py-1.5 text-sm transition-colors",
                    b === bucket ? "text-fg" : "text-muted hover:bg-panel hover:text-fg",
                  )}
                >
                  <button
                    onClick={() => {
                      setBucket(b);
                      setOpen(false);
                    }}
                    className="flex min-w-0 flex-1 items-center gap-2 text-left"
                  >
                    <span className="truncate">{b}</span>
                    {b === bucket && <Check size={14} className="ml-auto shrink-0 text-accent" />}
                  </button>
                  {b !== "default" && (
                    <button
                      onClick={() => {
                        setOpen(false);
                        setConfirm(b);
                        setConfirmText("");
                      }}
                      title="Delete bucket"
                      className="shrink-0 text-faint opacity-0 transition-colors hover:text-danger group-hover:opacity-100"
                    >
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
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

      <Modal open={confirm !== null} onClose={() => !deleting && setConfirm(null)}>
        <h3 className="font-display text-lg font-bold text-fg">Delete bucket</h3>
        <p className="mt-2 text-sm leading-relaxed text-muted">
          This permanently deletes <span className="font-mono text-fg">{confirm}</span> and all of its
          files, chunks, and embeddings from the RAG. This cannot be undone.
        </p>
        <label className="mt-5 flex flex-col gap-1.5">
          <span className="font-mono text-[10px] uppercase tracking-wider text-faint">
            type <span className="text-muted">{confirm}</span> to confirm
          </span>
          <input
            autoFocus
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && doDelete()}
            className="rounded-md border border-line bg-bg px-3 py-2 font-mono text-sm text-fg outline-none focus:border-danger"
          />
        </label>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setConfirm(null)} disabled={deleting}>
            Cancel
          </Button>
          <Button variant="danger" onClick={doDelete} disabled={confirmText !== confirm || deleting}>
            {deleting ? "Deleting…" : "Delete bucket"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
