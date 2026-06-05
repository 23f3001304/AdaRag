"use client";

import { Plus, Search, Trash2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";

interface ChatItem {
  id: string;
  title: string;
  turns: { text: string }[];
}

// The chats sidebar: new chat, a search box that matches titles + message text across all chats,
// and the (optionally filtered) list with a matching snippet under each hit.
export function ChatList({
  chats,
  activeId,
  onSelect,
  onAdd,
  onDelete,
}: {
  chats: ChatItem[];
  activeId: string;
  onSelect: (id: string) => void;
  onAdd: () => void;
  onDelete: (id: string) => void;
}) {
  const [q, setQ] = useState("");
  const needle = q.trim().toLowerCase();

  const matches = (c: ChatItem) =>
    c.title.toLowerCase().includes(needle) || c.turns.some((t) => t.text.toLowerCase().includes(needle));
  const shown = needle ? chats.filter(matches) : chats;

  const snippetOf = (c: ChatItem): string | null => {
    if (!needle) return null;
    const turn = c.turns.find((t) => t.text.toLowerCase().includes(needle));
    if (!turn) return null;
    const at = turn.text.toLowerCase().indexOf(needle);
    const start = Math.max(0, at - 24);
    return `${start > 0 ? "…" : ""}${turn.text.slice(start, at + needle.length + 36)}…`;
  };

  return (
    <aside className="flex w-52 shrink-0 flex-col gap-2">
      <Button onClick={onAdd} variant="outline" className="justify-start">
        <Plus size={14} /> New chat
      </Button>
      <div className="relative">
        <Search size={13} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-faint" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="search all chats…"
          className="w-full rounded-md border border-line bg-bg py-1.5 pl-8 pr-2 text-xs text-fg outline-none placeholder:text-faint focus:border-line-2"
        />
      </div>
      <div className="flex flex-1 flex-col gap-0.5 overflow-y-auto">
        {shown.map((c) => {
          const snippet = snippetOf(c);
          return (
            <div
              key={c.id}
              onClick={() => onSelect(c.id)}
              className={cn(
                "group flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-2 text-sm transition-colors",
                c.id === activeId ? "bg-panel text-fg" : "text-muted hover:bg-panel hover:text-fg",
              )}
            >
              <div className="min-w-0 flex-1">
                <span className="block truncate">{c.title}</span>
                {snippet && (
                  <span className="mt-0.5 block truncate font-mono text-[10px] text-faint">{snippet}</span>
                )}
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(c.id);
                }}
                className="shrink-0 text-faint opacity-0 transition-opacity hover:text-danger group-hover:opacity-100"
              >
                <Trash2 size={13} />
              </button>
            </div>
          );
        })}
        {needle && shown.length === 0 && (
          <p className="px-2 py-6 text-center text-xs text-faint">no matching chats.</p>
        )}
      </div>
    </aside>
  );
}
