"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

import { useNotify } from "@/components/notification-context";
import { api } from "@/lib/api";

const KEY = "adarag.ingest";

export type Stage = "idle" | "profile" | "chunk" | "embed" | "index" | "done" | "error";
export interface IngestDoc {
  source: string;
  chunks: number;
  modality: string;
  profile: string;
}

const ORDER = ["profile", "chunk", "embed", "index"] as const;
const MS = { profile: 850, chunk: 950, embed: 1050, index: 1150 };

function inferModality(name: string): string {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  if (["png", "jpg", "jpeg", "webp", "gif", "bmp"].includes(ext)) return "image";
  if (["wav", "mp3", "m4a", "flac", "ogg"].includes(ext)) return "audio";
  if (["mp4", "mov", "mkv", "webm", "avi"].includes(ext)) return "video";
  return "text";
}

interface IngestState {
  doc: IngestDoc | null;
  stage: Stage;
  note: string;
  ingest: (file: File, bucket: string, context?: string) => void;
  playSample: (d: IngestDoc) => void;
}

const Ctx = createContext<IngestState | null>(null);

export function useIngest(): IngestState {
  const c = useContext(Ctx);
  if (!c) throw new Error("useIngest must be used within IngestProvider");
  return c;
}

// Holds ingest progress at the app level so it survives tab switches, and only marks "done" when
// the real /ingest call resolves (the stage animation holds at "index" until then).
export function IngestProvider({ children }: { children: React.ReactNode }) {
  const { notify } = useNotify();
  const [doc, setDoc] = useState<IngestDoc | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [note, setNote] = useState("");
  const timers = useRef<number[]>([]);
  const bucketRef = useRef("default");

  // Survive a full refresh: rehydrate the last ingest, and if a refresh dropped an in-flight
  // request, confirm against the backend (the file may have finished indexing server-side).
  useEffect(() => {
    let saved: { doc: IngestDoc | null; stage: Stage; note: string; bucket: string } | null = null;
    try {
      saved = JSON.parse(localStorage.getItem(KEY) ?? "null");
    } catch {
      saved = null;
    }
    if (!saved) return;
    // Rehydrating persisted client state on mount is intended here; a lazy initializer would
    // read localStorage during SSR and mismatch on hydration.
    /* eslint-disable react-hooks/set-state-in-effect */
    setDoc(saved.doc);
    setStage(saved.stage);
    setNote(saved.note);
    /* eslint-enable react-hooks/set-state-in-effect */
    bucketRef.current = saved.bucket;
    if ((ORDER as readonly string[]).includes(saved.stage) && saved.doc) {
      const source = saved.doc.source;
      api
        .listDocuments(saved.bucket)
        .then((r) => {
          const hit = r.documents.find((d) => d.source === source);
          if (hit) {
            setDoc((d) => (d ? { ...d, chunks: hit.chunks } : d));
            setStage("done");
          } else {
            setNote("indexing was interrupted by the refresh - re-ingest if the file is missing.");
          }
        })
        .catch(() => {});
    }
  }, []);

  // Persist progress so a tab refresh keeps showing it (tab switches already survive in memory).
  useEffect(() => {
    if (stage === "idle" && !doc) return; // don't clobber a saved state with the empty initial
    try {
      localStorage.setItem(KEY, JSON.stringify({ doc, stage, note, bucket: bucketRef.current }));
    } catch {
      // best-effort: ignore quota/serialization errors
    }
  }, [doc, stage, note]);

  const animate = useCallback((d: IngestDoc, hold: boolean) => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    setNote("");
    setDoc(d);
    let at = 0;
    for (const s of ORDER) {
      timers.current.push(window.setTimeout(() => setStage(s), at));
      at += MS[s];
    }
    if (!hold) timers.current.push(window.setTimeout(() => setStage("done"), at));
  }, []);

  const finish = (chunks: number) => {
    setDoc((d) => (d ? { ...d, chunks } : d));
    setStage("done");
    window.dispatchEvent(new Event("adarag:ingested")); // nudge the clarification poll
  };

  const ingest = useCallback(
    async (file: File, bucket: string, context = "") => {
      bucketRef.current = bucket;
      const modality = inferModality(file.name);
      animate(
        {
          source: file.name,
          chunks: Math.max(4, Math.round(file.size / 1800)),
          modality,
          profile: modality === "text" ? "prose" : modality,
        },
        true, // hold at "index" until the real ingest resolves
      );
      try {
        finish((await api.ingest(file, bucket, context)).chunks);
        notify({ kind: "success", title: "Ingested", body: file.name });
      } catch {
        // A slow image can outrun the proxy while the server finishes. If the file actually
        // landed, show done instead of a misleading error.
        const landed = await api
          .listDocuments(bucket)
          .then((r) => r.documents.find((d) => d.source === file.name))
          .catch(() => undefined);
        if (landed) {
          finish(landed.chunks);
          notify({ kind: "success", title: "Ingested", body: file.name });
        } else {
          setNote("ingest failed - is the CLI bridge running?");
          setStage("error");
          notify({ kind: "error", title: "Ingest failed", body: file.name });
        }
      }
    },
    [animate, notify],
  );

  const playSample = useCallback((d: IngestDoc) => animate(d, false), [animate]);

  return (
    <Ctx.Provider value={{ doc, stage, note, ingest, playSample }}>{children}</Ctx.Provider>
  );
}
