"use client";

import { FileText, Image as ImageIcon, Music, RefreshCw, Video } from "lucide-react";
import { type ComponentType, useCallback, useEffect, useState } from "react";

import { Button, Panel } from "@/components/ui";
import { type DocumentInfo, api } from "@/lib/api";

const MOD_ICON: Record<string, ComponentType<{ size?: number; className?: string }>> = {
  text: FileText,
  image: ImageIcon,
  audio: Music,
  video: Video,
};
const MOD_COLOR: Record<string, string> = {
  text: "text-mod-text",
  image: "text-mod-image",
  audio: "text-mod-audio",
  video: "text-mod-video",
};

export default function FilesPage() {
  const [docs, setDocs] = useState<DocumentInfo[] | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setError("");
    setDocs(null);
    api
      .listDocuments("default")
      .then((r) => setDocs(r.documents))
      .catch((e) => {
        setDocs([]);
        setError(String(e).includes("Failed to fetch") ? "offline" : "stale");
      });
  }, []);
  useEffect(() => load(), [load]);

  const total = docs?.reduce((s, d) => s + d.chunks, 0) ?? 0;

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="font-display text-2xl font-bold tracking-tight text-fg">Files</h2>
          <p className="mt-1.5 text-sm text-muted">
            Everything indexed in this bucket
            {docs && docs.length > 0 ? ` · ${docs.length} files · ${total} chunks` : ""}.
          </p>
        </div>
        <Button variant="outline" onClick={load}>
          <RefreshCw size={14} /> Refresh
        </Button>
      </div>

      <Panel className="overflow-hidden">
        <div className="grid grid-cols-[1fr_110px_80px] gap-4 border-b border-line px-5 py-2.5 font-mono text-[10px] uppercase tracking-wider text-faint">
          <span>source</span>
          <span>modality</span>
          <span className="text-right">chunks</span>
        </div>
        {docs === null ? (
          <Empty>loading…</Empty>
        ) : docs.length === 0 ? (
          <Empty>
            {error === "offline"
              ? "backend offline - start it, then ingest a file from the Ingest tab."
              : error === "stale"
                ? "the /documents endpoint is missing - rebuild the backend image."
                : "No files yet. Ingest one from the Ingest tab."}
          </Empty>
        ) : (
          docs.map((d) => {
            const Icon = MOD_ICON[d.modality] ?? FileText;
            return (
              <div
                key={d.source}
                className="grid grid-cols-[1fr_110px_80px] items-center gap-4 border-b border-line px-5 py-3 last:border-0 hover:bg-panel-2/40"
              >
                <span className="flex min-w-0 items-center gap-2.5">
                  <Icon size={15} className={MOD_COLOR[d.modality] ?? "text-mod-text"} />
                  <span className="truncate font-mono text-sm text-fg">{d.source}</span>
                </span>
                <span className="font-mono text-xs capitalize text-muted">{d.modality}</span>
                <span className="text-right font-mono text-sm tabular-nums text-fg">{d.chunks}</span>
              </div>
            );
          })
        )}
      </Panel>
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <div className="px-5 py-10 text-center text-sm text-muted">{children}</div>;
}
