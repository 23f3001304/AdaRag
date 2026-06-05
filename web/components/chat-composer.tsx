"use client";

import { CornerDownLeft, Paperclip, X } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui";

// The chat input: a message field, a paperclip to attach a file, and send. An attached file is
// staged as a chip; on send it goes up with the text so the backend can route ingest vs ask.
export function ChatComposer({
  onSend,
  busy,
}: {
  onSend: (text: string, file: File | null) => Promise<void>;
  busy: boolean;
}) {
  const [msg, setMsg] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const submit = async () => {
    const text = msg.trim();
    if ((!text && !file) || busy) return;
    const staged = file;
    setMsg("");
    setFile(null);
    if (fileRef.current) fileRef.current.value = "";
    await onSend(text, staged);
  };

  return (
    <div className="border-t border-line p-3">
      {file && (
        <div className="mb-2 flex w-fit max-w-full items-center gap-1.5 rounded-md border border-line bg-bg px-2 py-1 text-xs text-muted">
          <Paperclip size={12} className="shrink-0 text-accent" />
          <span className="truncate">{file.name}</span>
          <button onClick={() => setFile(null)} className="shrink-0 text-faint hover:text-danger">
            <X size={12} />
          </button>
        </div>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="flex gap-2"
      >
        <input
          ref={fileRef}
          type="file"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          title="Attach a file to ingest"
          className="flex size-10 shrink-0 items-center justify-center rounded-md border border-line bg-bg text-faint transition-colors hover:border-line-2 hover:text-accent"
        >
          <Paperclip size={15} />
        </button>
        <input
          value={msg}
          onChange={(e) => setMsg(e.target.value)}
          placeholder={file ? "say 'ingest it' to add this file…" : "ask a question…"}
          className="flex-1 rounded-md border border-line bg-bg px-3 py-2.5 text-sm text-fg outline-none placeholder:text-faint focus:border-line-2"
        />
        <Button type="submit" disabled={busy}>
          <CornerDownLeft size={14} /> Send
        </Button>
      </form>
    </div>
  );
}
