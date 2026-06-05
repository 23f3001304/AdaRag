"use client";

import { Download, X } from "lucide-react";

import { Modal } from "@/components/modal";
import { api } from "@/lib/api";

export interface Resource {
  path: string;
  name: string;
  modality: string;
}

// Preview a preserved original inline (image / audio / video) with a download fallback.
export function ResourceModal({ resource, onClose }: { resource: Resource | null; onClose: () => void }) {
  return (
    <Modal open={resource !== null} onClose={onClose} className="max-w-2xl">
      {resource && (
        <>
          <div className="mb-4 flex items-center justify-between gap-3">
            <h3 className="truncate font-mono text-sm text-fg">{resource.name}</h3>
            <div className="flex shrink-0 items-center gap-3">
              <a
                href={api.fileUrl(resource.path, resource.name)}
                download
                className="flex items-center gap-1.5 rounded-md border border-line bg-bg px-2.5 py-1.5 text-xs text-fg transition-colors hover:border-line-2"
              >
                <Download size={13} /> Download
              </a>
              <button onClick={onClose} className="text-faint transition-colors hover:text-fg">
                <X size={16} />
              </button>
            </div>
          </div>
          <div className="flex max-h-[60vh] items-center justify-center overflow-auto rounded-lg border border-line bg-bg p-3">
            {resource.modality === "image" ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={api.fileUrl(resource.path)} alt={resource.name} className="max-h-[55vh] max-w-full rounded" />
            ) : resource.modality === "audio" ? (
              <audio controls src={api.fileUrl(resource.path)} className="w-full" />
            ) : resource.modality === "video" ? (
              <video controls src={api.fileUrl(resource.path)} className="max-h-[55vh] max-w-full rounded" />
            ) : (
              <p className="px-4 py-10 text-center text-sm text-muted">
                No inline preview for this type. Use Download.
              </p>
            )}
          </div>
        </>
      )}
    </Modal>
  );
}
