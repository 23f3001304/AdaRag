"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { useBucket } from "@/components/bucket-context";
import { type Clarification, api } from "@/lib/api";

interface ClarificationState {
  items: Clarification[];
  refresh: () => void;
  answer: (id: string, entity: string) => Promise<void>;
  dismiss: (id: string) => Promise<void>;
}

const Ctx = createContext<ClarificationState | null>(null);

export function useClarifications(): ClarificationState {
  const c = useContext(Ctx);
  if (!c) throw new Error("useClarifications must be used within ClarificationProvider");
  return c;
}

// Polls the active bucket's pending clarifications so the nav badge, the toast, and the Ingest
// panel all share one live list. Ingest fires these in the background, so we poll rather than push.
export function ClarificationProvider({ children }: { children: React.ReactNode }) {
  const { bucket } = useBucket();
  const [items, setItems] = useState<Clarification[]>([]);

  const refresh = useCallback(() => {
    api
      .listClarifications(bucket)
      .then((r) => setItems(r.clarifications))
      .catch(() => {});
  }, [bucket]);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 10_000);
    window.addEventListener("focus", refresh);
    return () => {
      clearInterval(id);
      window.removeEventListener("focus", refresh);
    };
  }, [refresh]);

  const answer = useCallback(async (id: string, entity: string) => {
    await api.answerClarification(id, entity);
    setItems((xs) => xs.filter((x) => x.id !== id));
  }, []);

  const dismiss = useCallback(async (id: string) => {
    await api.dismissClarification(id);
    setItems((xs) => xs.filter((x) => x.id !== id));
  }, []);

  return <Ctx.Provider value={{ items, refresh, answer, dismiss }}>{children}</Ctx.Provider>;
}
