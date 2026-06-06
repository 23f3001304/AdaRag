"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

export type NotifyKind = "success" | "info" | "error" | "ask";

export interface AppNotification {
  id: string;
  kind: NotifyKind;
  title: string;
  body?: string;
  href?: string; // a notification that links somewhere (e.g. a clarification -> Ingest) never expires
}

interface NotifyState {
  items: AppNotification[];
  notify: (n: Omit<AppNotification, "id">) => void;
  dismiss: (id: string) => void;
  pause: () => void; // hold the auto-dismiss timers while the stack is expanded for reading
  resume: () => void;
}

const Ctx = createContext<NotifyState | null>(null);
const LIFE = 5000;

export function useNotify(): NotifyState {
  const c = useContext(Ctx);
  if (!c) throw new Error("useNotify must be used within NotificationProvider");
  return c;
}

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<AppNotification[]>([]);
  const itemsRef = useRef<AppNotification[]>([]);
  useEffect(() => {
    itemsRef.current = items; // mirror for resume() to re-arm timers without a stale closure
  }, [items]);
  const timers = useRef<Map<string, number>>(new Map());

  const dismiss = useCallback((id: string) => {
    const t = timers.current.get(id);
    if (t) clearTimeout(t);
    timers.current.delete(id);
    setItems((xs) => xs.filter((x) => x.id !== id));
  }, []);

  const arm = useCallback(
    (id: string) => timers.current.set(id, window.setTimeout(() => dismiss(id), LIFE)),
    [dismiss],
  );

  const notify = useCallback(
    (n: Omit<AppNotification, "id">) => {
      const id = crypto.randomUUID();
      setItems((xs) => [...xs, { ...n, id }].slice(-5));
      arm(id);
    },
    [arm],
  );

  // Let any code fire a toast without the hook: window.dispatchEvent(new CustomEvent("adarag:notify",
  // { detail: { kind, title, body } })). Decouples notifications from the React tree.
  useEffect(() => {
    const handler = (e: Event) => notify((e as CustomEvent<Omit<AppNotification, "id">>).detail);
    window.addEventListener("adarag:notify", handler);
    return () => window.removeEventListener("adarag:notify", handler);
  }, [notify]);

  const pause = useCallback(() => {
    timers.current.forEach((t) => clearTimeout(t));
    timers.current.clear();
  }, []);

  const resume = useCallback(() => {
    itemsRef.current.forEach((x) => !timers.current.has(x.id) && arm(x.id));
  }, [arm]);

  return (
    <Ctx.Provider value={{ items, notify, dismiss, pause, resume }}>{children}</Ctx.Provider>
  );
}
