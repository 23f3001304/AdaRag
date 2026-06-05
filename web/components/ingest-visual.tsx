"use client";

import { Boxes, Database, FileText, Layers, ScanLine } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { Fragment, useCallback, useRef, useState } from "react";

import { Button } from "@/components/ui";
import { VectorField } from "@/components/vector-field";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";

const STAGES = [
  { key: "profile", label: "Profile", icon: ScanLine },
  { key: "chunk", label: "Chunk", icon: Layers },
  { key: "embed", label: "Embed", icon: Boxes },
  { key: "index", label: "Index", icon: Database },
] as const;

type StageKey = (typeof STAGES)[number]["key"];
type Stage = "idle" | StageKey | "done";
const ORDER: StageKey[] = ["profile", "chunk", "embed", "index"];
const MS: Record<StageKey, number> = { profile: 850, chunk: 950, embed: 1050, index: 1150 };

interface Doc {
  source: string;
  chunks: number;
  modality: string;
  profile: string;
}

const SAMPLE: Doc = {
  source: "attention_is_all_you_need.pdf",
  chunks: 24,
  modality: "text",
  profile: "paper",
};

function inferModality(name: string): string {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  if (["png", "jpg", "jpeg", "webp", "gif", "bmp"].includes(ext)) return "image";
  if (["wav", "mp3", "m4a", "flac", "ogg"].includes(ext)) return "audio";
  if (["mp4", "mov", "mkv", "webm", "avi"].includes(ext)) return "video";
  return "text";
}

export function IngestVisual({ bucket = "default" }: { bucket?: string }) {
  const [stage, setStage] = useState<Stage>("idle");
  const [doc, setDoc] = useState<Doc | null>(null);
  const [note, setNote] = useState("");
  const timers = useRef<number[]>([]);
  const fileInput = useRef<HTMLInputElement>(null);

  const idx = stage === "done" ? ORDER.length : stage === "idle" ? -1 : ORDER.indexOf(stage);

  const play = useCallback((d: Doc) => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    setDoc(d);
    let at = 0;
    for (const s of ORDER) {
      timers.current.push(window.setTimeout(() => setStage(s), at));
      at += MS[s];
    }
    timers.current.push(window.setTimeout(() => setStage("done"), at));
  }, []);

  const onFile = useCallback(
    async (file: File) => {
      const modality = inferModality(file.name);
      setNote("");
      play({
        source: file.name,
        chunks: Math.max(4, Math.round(file.size / 1800)),
        modality,
        profile: modality === "text" ? "prose" : modality,
      });
      try {
        const res = await api.ingest(file, bucket);
        setDoc((d) => (d ? { ...d, chunks: res.chunks, source: res.source } : d));
      } catch {
        setNote("backend offline - counts are estimated");
      }
    },
    [bucket, play],
  );

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-2">
        {STAGES.map((s, i) => {
          const active = idx === i;
          const done = idx > i;
          return (
            <Fragment key={s.key}>
              <div
                className={cn(
                  "flex items-center gap-2 rounded-md border px-3 py-1.5 transition-colors duration-300",
                  active
                    ? "border-accent/60 bg-accent/10 text-fg"
                    : done
                      ? "border-line-2 text-muted"
                      : "border-line text-faint",
                )}
              >
                <s.icon size={14} className={cn(active && "text-accent")} />
                <span className="font-mono text-xs">{s.label}</span>
              </div>
              {i < STAGES.length - 1 && (
                <div className="relative h-px flex-1 overflow-hidden bg-line">
                  <motion.div
                    className="absolute inset-y-0 left-0 bg-accent"
                    animate={{ width: done ? "100%" : "0%" }}
                    transition={{ duration: 0.4 }}
                  />
                </div>
              )}
            </Fragment>
          );
        })}
      </div>

      <div className="grid min-h-[290px] grid-cols-[1fr_1fr] gap-5 rounded-xl border border-line bg-panel/40 p-5">
        <div className="flex flex-col gap-4 border-r border-line pr-5">
          <AnimatePresence>
            {doc && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="relative overflow-hidden rounded-lg border border-line bg-bg p-4"
              >
                <div className="flex items-center gap-3">
                  <FileText size={18} className="text-mod-text" />
                  <span className="truncate font-mono text-xs text-fg">{doc.source}</span>
                  <span className="ml-auto rounded border border-line px-1.5 py-px font-mono text-[10px] uppercase tracking-wider text-muted">
                    {doc.profile}
                  </span>
                </div>
                {stage === "profile" && (
                  <motion.div
                    className="absolute inset-x-0 h-8 bg-gradient-to-b from-transparent via-accent/20 to-transparent"
                    initial={{ top: "-2rem" }}
                    animate={{ top: "100%" }}
                    transition={{ duration: 0.75, repeat: Infinity }}
                  />
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {doc && idx >= 1 && (
            <div>
              <span className="font-mono text-[10px] uppercase tracking-wider text-faint">
                chunks
              </span>
              <div className="mt-2 grid grid-cols-6 gap-1.5">
                {Array.from({ length: Math.min(doc.chunks, 18) }).map((_, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.03, type: "spring", stiffness: 300, damping: 20 }}
                    className="h-5 rounded-[3px] border border-line bg-panel-2"
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-col">
          <span className="font-mono text-[10px] uppercase tracking-wider text-faint">
            vector space · bge-m3 · 1024d
          </span>
          <div className="mt-2 flex flex-1">
            <VectorField
              count={doc?.chunks ?? 0}
              modality={doc?.modality ?? "text"}
              active={!!doc && idx >= 2}
            />
          </div>
        </div>
      </div>

      <div className="flex items-end justify-between">
        <div className="flex gap-7">
          <Metric label="chunks" value={doc ? String(doc.chunks) : "-"} />
          <Metric label="dim" value="1024" />
          <Metric label="modality" value={doc?.modality ?? "-"} />
          <Metric label="stage" value={stage} />
        </div>
        <div className="flex gap-2">
          <input
            ref={fileInput}
            type="file"
            hidden
            onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
          />
          <Button variant="outline" onClick={() => fileInput.current?.click()}>
            Upload a file
          </Button>
          <Button onClick={() => play(SAMPLE)}>Play sample</Button>
        </div>
      </div>
      {note && <p className="font-mono text-xs text-muted">{note}</p>}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-mono text-[10px] uppercase tracking-wider text-faint">{label}</span>
      <span className="font-mono text-sm tabular-nums text-fg">{value}</span>
    </div>
  );
}
