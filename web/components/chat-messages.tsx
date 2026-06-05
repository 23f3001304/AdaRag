"use client";

import { Brain, ChevronDown, Paperclip, User } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";

import { Logo } from "@/components/logo";
import { MarkdownMessage } from "@/components/markdown-message";
import type { Resource } from "@/components/resource-modal";
import { cn } from "@/lib/cn";

export interface Source {
  source: string;
  path: string | null;
  modality: string;
}
export interface Turn {
  role: "user" | "assistant";
  text: string;
  query?: string;
  sources?: Source[];
  file?: string;
  thinking?: string;
}

export function ChatMessages({
  turns,
  busy,
  bucket,
  onPreview,
}: {
  turns: Turn[];
  busy: boolean;
  bucket: string;
  onPreview: (r: Resource) => void;
}) {
  return (
    <>
      {turns.length === 0 && !busy && (
        <p className="mt-16 text-center text-sm text-faint">
          Ask anything about the <span className="text-muted">{bucket}</span> bucket, attach a file
          and say &ldquo;ingest it&rdquo;, or type <span className="text-muted">/</span> for skills.
        </p>
      )}
      <AnimatePresence initial={false}>
        {turns.map((t, i) => (
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
              {t.text &&
                (t.role === "assistant" ? (
                  <MarkdownMessage text={t.text} />
                ) : (
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-fg">{t.text}</p>
                ))}
              {t.thinking && <ThinkingBlock text={t.thinking} live={!t.text} />}
              {t.sources && t.sources.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {t.sources.map((s) =>
                    s.path ? (
                      <button
                        key={s.source}
                        onClick={() => onPreview({ path: s.path!, name: s.source, modality: s.modality })}
                        title="Open source"
                        className="flex items-center gap-1 rounded border border-line px-1.5 py-px font-mono text-[10px] text-muted transition-colors hover:border-accent/50 hover:text-fg"
                      >
                        {s.source}
                      </button>
                    ) : (
                      <span
                        key={s.source}
                        className="truncate rounded border border-line px-1.5 py-px font-mono text-[10px] text-muted"
                      >
                        {s.source}
                      </span>
                    ),
                  )}
                </div>
              )}
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
      {busy && turns[turns.length - 1]?.role !== "assistant" && (
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
    </>
  );
}

function ThinkingBlock({ text, live }: { text: string; live: boolean }) {
  const [open, setOpen] = useState(false);
  const expanded = open || live; // auto-expand while the answer is still streaming
  return (
    <div className="mt-1">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 font-mono text-[10px] text-faint transition-colors hover:text-muted"
      >
        <Brain size={11} className={cn(live && "animate-pulse text-accent")} />
        {live ? "thinking…" : expanded ? "hide thinking" : "thinking"}
        <ChevronDown size={10} className={cn("transition-transform", expanded && "rotate-180")} />
      </button>
      {expanded && (
        <div className="mt-1 whitespace-pre-wrap rounded-md border border-line bg-bg/50 p-2.5 text-xs italic leading-relaxed text-muted">
          {text}
        </div>
      )}
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
