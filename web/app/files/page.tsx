"use client";

import { Download, Eye, FileText, Image as ImageIcon, Music, RefreshCw, Trash2, Video } from "lucide-react";
import { type ComponentType, useCallback, useEffect, useState } from "react";

import { useBucket } from "@/components/bucket-context";
import { Modal } from "@/components/modal";
import { type Resource, ResourceModal } from "@/components/resource-modal";
import { Button, Panel } from "@/components/ui";
import { type DocumentInfo, api, downloadFile } from "@/lib/api";

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
const VIEWABLE = new Set(["image", "audio", "video"]);

export default function FilesPage() {
  const { bucket } = useBucket();
  const [docs, setDocs] = useState<DocumentInfo[] | null>(null);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<Resource | null>(null);
  const [confirmDel, setConfirmDel] = useState<DocumentInfo | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [note, setNote] = useState("");

  const load = useCallback(() => {
    setError("");
    setDocs(null);
    api
      .listDocuments(bucket)
      .then((r) => setDocs(r.documents))
      .catch((e) => {
        setDocs([]);
        setError(String(e).includes("Failed to fetch") ? "offline" : "stale");
      });
  }, [bucket]);
  useEffect(() => load(), [load]);

  const doDelete = async () => {
    if (!confirmDel || deleting) return;
    setDeleting(true);
    try {
      await api.deleteDocument(bucket, confirmDel.source);
      setConfirmDel(null);
      load();
    } catch {
      /* keep the modal open on failure */
    } finally {
      setDeleting(false);
    }
  };

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
          {note && <p className="mt-1 text-xs text-danger">{note}</p>}
        </div>
        <Button variant="outline" onClick={load}>
          <RefreshCw size={14} /> Refresh
        </Button>
      </div>

      <Panel className="overflow-hidden">
        <div className="grid grid-cols-[1fr_88px_56px_108px] gap-4 border-b border-line px-5 py-2.5 font-mono text-[10px] uppercase tracking-wider text-faint">
          <span>source</span>
          <span>modality</span>
          <span className="text-right">chunks</span>
          <span />
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
            const path = d.original_path;
            return (
              <div
                key={d.source}
                className="group grid grid-cols-[1fr_88px_56px_108px] items-center gap-4 border-b border-line px-5 py-3 last:border-0 hover:bg-panel-2/40"
              >
                <span className="flex min-w-0 items-center gap-2.5">
                  <Icon size={15} className={MOD_COLOR[d.modality] ?? "text-mod-text"} />
                  <span className="truncate font-mono text-sm text-fg">{d.source}</span>
                </span>
                <span className="font-mono text-xs capitalize text-muted">{d.modality}</span>
                <span className="text-right font-mono text-sm tabular-nums text-fg">{d.chunks}</span>
                <span className="flex items-center justify-end gap-2.5 text-faint opacity-0 transition-opacity group-hover:opacity-100">
                  {path && VIEWABLE.has(d.modality) && (
                    <button
                      title="Preview"
                      onClick={() => setPreview({ path, name: d.source, modality: d.modality })}
                      className="transition-colors hover:text-fg"
                    >
                      <Eye size={15} />
                    </button>
                  )}
                  {path && (
                    <button
                      title="Download"
                      onClick={() =>
                        downloadFile(path, d.source).catch((e) =>
                          setNote(`${d.source}: ${e instanceof Error ? e.message : e}`),
                        )
                      }
                      className="transition-colors hover:text-fg"
                    >
                      <Download size={15} />
                    </button>
                  )}
                  <button
                    title="Delete"
                    onClick={() => setConfirmDel(d)}
                    className="transition-colors hover:text-danger"
                  >
                    <Trash2 size={14} />
                  </button>
                </span>
              </div>
            );
          })
        )}
      </Panel>

      <ResourceModal resource={preview} onClose={() => setPreview(null)} />

      <Modal open={confirmDel !== null} onClose={() => !deleting && setConfirmDel(null)}>
        <h3 className="font-display text-lg font-bold text-fg">Delete file</h3>
        <p className="mt-2 text-sm leading-relaxed text-muted">
          Remove <span className="font-mono text-fg">{confirmDel?.source}</span> and its{" "}
          {confirmDel?.chunks} chunk{confirmDel?.chunks === 1 ? "" : "s"} from this bucket, plus its
          stored original. This cannot be undone.
        </p>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setConfirmDel(null)} disabled={deleting}>
            Cancel
          </Button>
          <Button variant="danger" onClick={doDelete} disabled={deleting}>
            {deleting ? "Deleting…" : "Delete"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <div className="px-5 py-10 text-center text-sm text-muted">{children}</div>;
}
