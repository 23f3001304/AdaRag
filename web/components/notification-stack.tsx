"use client";

import { ArrowUpRight, Check, HelpCircle, Info, TriangleAlert, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ComponentType, useMemo, useState } from "react";

import { useClarifications } from "@/components/clarification-context";
import { type AppNotification, type NotifyKind, useNotify } from "@/components/notification-context";
import { cn } from "@/lib/cn";

const STYLE: Record<NotifyKind, { icon: ComponentType<{ size?: number }>; ring: string }> = {
  success: { icon: Check, ring: "bg-accent/15 text-accent" },
  info: { icon: Info, ring: "bg-mod-text/15 text-mod-text" },
  error: { icon: TriangleAlert, ring: "bg-danger/15 text-danger" },
  ask: { icon: HelpCircle, ring: "bg-accent/15 text-accent" },
};

const H = 64; // fixed card height keeps the stack maths simple
const GAP = 10;

// A corner notification center: collapsed it peeks as a tidy stack; on hover it fans into a list.
// Transient toasts auto-dismiss; the clarification nudge persists (with a link) until answered.
export function NotificationStack() {
  const { items, dismiss, pause, resume } = useNotify();
  const { items: clarifs } = useClarifications();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const cards = useMemo<AppNotification[]>(() => {
    const list = [...items].reverse(); // newest in front
    if (clarifs.length && pathname !== "/ingest") {
      list.unshift({
        id: "__clarifications",
        kind: "ask",
        title: `${clarifs.length} file${clarifs.length === 1 ? "" : "s"} need a name`,
        body: "answer on the Ingest tab",
        href: "/ingest",
      });
    }
    return list.slice(0, 5);
  }, [items, clarifs, pathname]);

  if (!cards.length) return null;

  return (
    <div
      className="fixed bottom-5 right-5 z-50 w-[330px]"
      style={{ height: open ? cards.length * (H + GAP) : H + 22 }}
      onMouseEnter={() => {
        setOpen(true);
        pause();
      }}
      onMouseLeave={() => {
        setOpen(false);
        resume();
      }}
    >
      <AnimatePresence initial={false}>
        {cards.map((c, i) => (
          <motion.div
            key={c.id}
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{
              opacity: open ? 1 : i < 3 ? 1 - i * 0.16 : 0,
              y: open ? -i * (H + GAP) : -i * 9,
              scale: open ? 1 : 1 - i * 0.05,
            }}
            exit={{ opacity: 0, y: 12, scale: 0.9 }}
            transition={{ type: "spring", stiffness: 420, damping: 34 }}
            style={{ zIndex: cards.length - i }}
            className="absolute bottom-0 right-0 w-full"
          >
            <Card c={c} onDismiss={dismiss} />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

function Card({ c, onDismiss }: { c: AppNotification; onDismiss: (id: string) => void }) {
  const { icon: Icon, ring } = STYLE[c.kind];
  const inner = (
    <div className="flex h-16 items-center gap-3 rounded-xl border border-line bg-panel px-3.5 shadow-[0_12px_32px_-10px_rgba(0,0,0,0.65)]">
      <span className={cn("flex size-9 shrink-0 items-center justify-center rounded-full", ring)}>
        <Icon size={16} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-fg">{c.title}</p>
        {c.body && <p className="mt-0.5 truncate text-xs text-muted">{c.body}</p>}
      </div>
      {c.href ? (
        <ArrowUpRight size={15} className="shrink-0 text-accent" />
      ) : (
        <button
          onClick={(e) => {
            e.preventDefault();
            onDismiss(c.id);
          }}
          className="shrink-0 text-faint transition-colors hover:text-fg"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
  return c.href ? (
    <Link href={c.href} className="block">
      {inner}
    </Link>
  ) : (
    inner
  );
}
