"use client";

import { CornerDownLeft, Plus, Trash2, User } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";

import { useBucket } from "@/components/bucket-context";
import { Logo } from "@/components/logo";
import { Button } from "@/components/ui";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";

interface Turn {
  role: "user" | "assistant";
  text: string;
  query?: string;
  sources?: string[];
}
interface Chat {
  id: string;
  title: string;
  session: string;
  turns: Turn[];
}

const KEY = "adarag.chats";
const fresh = (): Chat => ({
  id: crypto.randomUUID(),
  title: "New chat",
  session: crypto.randomUUID(),
  turns: [],
});

export default function ChatPage() {
  const { bucket } = useBucket();
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeId, setActiveId] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let saved: Chat[] = [];
    try {
      saved = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    } catch {
      saved = [];
    }
    if (!saved.length) saved = [fresh()];
    setChats(saved);
    setActiveId(saved[0].id);
  }, []);

  const active = chats.find((c) => c.id === activeId);
  const persist = (next: Chat[]) => {
    setChats(next);
    localStorage.setItem(KEY, JSON.stringify(next));
  };

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [active?.turns.length, busy]);

  const addChat = () => {
    const c = fresh();
    persist([c, ...chats]);
    setActiveId(c.id);
  };
  const delChat = (id: string) => {
    const next = chats.filter((c) => c.id !== id);
    const safe = next.length ? next : [fresh()];
    persist(safe);
    if (id === activeId) setActiveId(safe[0].id);
  };

  const send = async () => {
    const text = msg.trim();
    if (!text || busy || !active) return;
    setMsg("");
    const withUser = chats.map((c) =>
      c.id === active.id
        ? {
            ...c,
            title: c.turns.length ? c.title : text.slice(0, 38),
            turns: [...c.turns, { role: "user" as const, text }],
          }
        : c,
    );
    persist(withUser);
    setBusy(true);
    try {
      const r = await api.chat(active.session, text, bucket);
      const sources = [...new Set(r.citations.map((c) => c.source))].slice(0, 5);
      persist(
        withUser.map((c) =>
          c.id === active.id
            ? { ...c, turns: [...c.turns, { role: "assistant", text: r.answer, query: r.search_query, sources }] }
            : c,
        ),
      );
    } catch (e) {
      const off = String(e).includes("Failed to fetch");
      persist(
        withUser.map((c) =>
          c.id === active.id
            ? {
                ...c,
                turns: [
                  ...c.turns,
                  { role: "assistant", text: off ? "backend offline." : "LLM backend errored - is the CLI bridge running?" },
                ],
              }
            : c,
        ),
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-5">
      <aside className="flex w-52 shrink-0 flex-col gap-2">
        <Button onClick={addChat} variant="outline" className="justify-start">
          <Plus size={14} /> New chat
        </Button>
        <div className="flex flex-1 flex-col gap-0.5 overflow-y-auto">
          {chats.map((c) => (
            <div
              key={c.id}
              onClick={() => setActiveId(c.id)}
              className={cn(
                "group flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-2 text-sm transition-colors",
                c.id === activeId ? "bg-panel text-fg" : "text-muted hover:bg-panel hover:text-fg",
              )}
            >
              <span className="truncate">{c.title}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  delChat(c.id);
                }}
                className="ml-auto shrink-0 text-faint opacity-0 transition-opacity hover:text-danger group-hover:opacity-100"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col rounded-xl border border-line bg-panel/30">
        <div className="flex-1 space-y-5 overflow-y-auto p-6">
          {active && active.turns.length === 0 && !busy && (
            <p className="mt-16 text-center text-sm text-faint">
              Ask anything about the <span className="text-muted">{bucket}</span> bucket.
            </p>
          )}
          <AnimatePresence initial={false}>
            {active?.turns.map((t, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3">
                <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-md border border-line bg-bg">
                  {t.role === "user" ? <User size={13} className="text-muted" /> : <Logo size={13} />}
                </span>
                <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                  {t.query && <span className="font-mono text-[10px] text-faint">searched: {t.query}</span>}
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-fg">{t.text}</p>
                  {t.sources && t.sources.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {t.sources.map((s) => (
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
              </motion.div>
            ))}
          </AnimatePresence>
          {busy && (
            <div className="flex gap-3">
              <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-md border border-line bg-bg">
                <Logo size={13} />
              </span>
              <div className="flex items-center gap-1 pt-1.5">
                {[0, 1, 2].map((i) => (
                  <motion.span
                    key={i}
                    className="size-1.5 rounded-full bg-muted"
                    animate={{ opacity: [0.25, 1, 0.25] }}
                    transition={{ duration: 1, repeat: Infinity, delay: i * 0.18 }}
                  />
                ))}
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
          className="flex gap-2 border-t border-line p-3"
        >
          <input
            value={msg}
            onChange={(e) => setMsg(e.target.value)}
            placeholder="ask a question…"
            className="flex-1 rounded-md border border-line bg-bg px-3 py-2.5 text-sm text-fg outline-none placeholder:text-faint focus:border-line-2"
          />
          <Button type="submit" disabled={busy}>
            <CornerDownLeft size={14} /> Send
          </Button>
        </form>
      </div>
    </div>
  );
}
