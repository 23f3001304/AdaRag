"use client";

import { Brain, ChevronDown, Paperclip, User } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";

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
                  <StreamingText text={t.text} live={busy && i === turns.length - 1} />
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

// Reveal chunky stream deltas (claude-cli emits ~60-80 chars at a time) as a smooth char-by-char
// type-out. Only this component re-renders per animation frame; the chat list stays paced by the
// network. A turn that was never live (history, page reloads) renders in full immediately.
function StreamingText({ text, live }: { text: string; live: boolean }) {
  const animate = useRef(live);
  if (live) animate.current = true;
  const [shown, setShown] = useState(animate.current ? 0 : text.length);
  const liveRef = useRef(live);
  liveRef.current = live;
  const lenRef = useRef(text.length);
  lenRef.current = text.length;
  const shownRef = useRef(shown);
  shownRef.current = shown;

  useEffect(() => {
    if (!animate.current) return;
    let raf = 0;
    let stopped = false;
    const tick = () => {
      if (stopped) return;
      const s = shownRef.current;
      const len = lenRef.current;
      if (s < len) {
        // Cap the per-frame step so a big delta types out steadily instead of popping in.
        // ~4 chars/frame at 60fps is a smooth typewriter that still keeps up with the stream.
        const step = Math.min(4, Math.max(1, Math.ceil((len - s) / 10)));
        const next = Math.min(len, s + step);
        shownRef.current = next;
        setShown(next);
      } else if (!liveRef.current) {
        return; // caught up and the stream finished - stop the loop for good
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => {
      stopped = true;
      cancelAnimationFrame(raf);
    };
  }, []);

  return <MarkdownMessage text={animate.current ? text.slice(0, shown) : text} />;
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
