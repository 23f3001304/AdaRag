"use client";

import { Paperclip, User } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";

import { useBucket } from "@/components/bucket-context";
import { ChatComposer } from "@/components/chat-composer";
import { ChatList } from "@/components/chat-list";
import { Logo } from "@/components/logo";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";

interface Turn {
  role: "user" | "assistant";
  text: string;
  query?: string;
  sources?: string[];
  file?: string; // filename attached to a user turn
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

  const send = async (text: string, file: File | null) => {
    if ((!text && !file) || busy || !active) return;
    const withUser = chats.map((c) =>
      c.id === active.id
        ? {
            ...c,
            title: c.turns.length ? c.title : text.slice(0, 38) || file?.name || "New chat",
            turns: [...c.turns, { role: "user" as const, text, file: file?.name }],
          }
        : c,
    );
    persist(withUser);
    const reply = (turn: Turn) =>
      persist(withUser.map((c) => (c.id === active.id ? { ...c, turns: [...c.turns, turn] } : c)));
    setBusy(true);
    try {
      if (file) {
        // The LLM routes the intent: "ingest it" adds the file; otherwise it's a normal question.
        const intent = text ? (await api.route(text)).intent : "ingest";
        if (intent === "ingest") {
          const res = await api.ingest(file, bucket);
          const n = res.chunks;
          reply({
            role: "assistant",
            text: `Ingested ${res.source} - ${n} chunk${n === 1 ? "" : "s"} into the ${bucket} bucket.`,
          });
          return;
        }
      }
      const r = await api.chat(active.session, text, bucket);
      const sources = [...new Set(r.citations.map((c) => c.source))].slice(0, 5);
      reply({ role: "assistant", text: r.answer, query: r.search_query, sources });
    } catch (e) {
      const off = String(e).includes("Failed to fetch");
      reply({
        role: "assistant",
        text: off ? "backend offline." : "request failed - is the CLI bridge running?",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-5">
      <ChatList
        chats={chats}
        activeId={activeId}
        onSelect={setActiveId}
        onAdd={addChat}
        onDelete={delChat}
      />

      <div className="flex min-w-0 flex-1 flex-col rounded-xl border border-line bg-panel/30">
        <div className="flex items-center justify-end border-b border-line px-4 py-2">
          <span className="font-mono text-[10px] text-faint">
            bucket: <span className="text-muted">{bucket}</span>
          </span>
        </div>
        <div className="flex-1 space-y-5 overflow-y-auto p-6">
          {active && active.turns.length === 0 && !busy && (
            <p className="mt-16 text-center text-sm text-faint">
              Ask anything about the <span className="text-muted">{bucket}</span> bucket, or attach a
              file and say &ldquo;ingest it&rdquo;.
            </p>
          )}
          <AnimatePresence initial={false}>
            {active?.turns.map((t, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-3"
              >
                <Avatar role={t.role} />
                <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                  {t.query && <span className="font-mono text-[10px] text-faint">searched: {t.query}</span>}
                  {t.file && (
                    <span className="flex w-fit items-center gap-1 rounded border border-line px-1.5 py-0.5 font-mono text-[10px] text-muted">
                      <Paperclip size={10} className="text-accent" /> {t.file}
                    </span>
                  )}
                  {t.text && <p className="whitespace-pre-wrap text-sm leading-relaxed text-fg">{t.text}</p>}
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
              <Avatar role="assistant" />
              <div className="flex items-center gap-1 pt-2">
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
        <ChatComposer onSend={send} busy={busy} />
      </div>
    </div>
  );
}

function Avatar({ role }: { role: "user" | "assistant" }) {
  return (
    <span
      className={cn(
        "mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full",
        role === "user" ? "bg-line-2 text-muted" : "bg-accent/15",
      )}
    >
      {role === "user" ? <User size={14} /> : <Logo size={14} />}
    </span>
  );
}
