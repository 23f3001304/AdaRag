"use client";

import { createContext, useCallback, useContext, useRef, useState } from "react";

import { api } from "@/lib/api";

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
  ingest: (file: File, bucket: string) => void;
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
  const [doc, setDoc] = useState<IngestDoc | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [note, setNote] = useState("");
  const timers = useRef<number[]>([]);

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

  const ingest = useCallback(
    async (file: File, bucket: string) => {
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
        const res = await api.ingest(file, bucket);
        setDoc((d) => (d ? { ...d, chunks: res.chunks, source: res.source } : d));
        setStage("done");
      } catch {
        setNote("ingest failed - is the CLI bridge running?");
        setStage("error");
      }
    },
    [animate],
  );

  const playSample = useCallback((d: IngestDoc) => animate(d, false), [animate]);

  return (
    <Ctx.Provider value={{ doc, stage, note, ingest, playSample }}>{children}</Ctx.Provider>
  );
}
