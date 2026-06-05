"use client";

import { Boxes, CornerDownLeft, Paperclip, Sparkles, X } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui";
import type { Skill } from "@/lib/skills";

// The chat input: a message field, a paperclip to attach a file, and a "/" menu to apply a saved
// skill or start the /skill-creator flow. An attached file rides up with the text for ingest routing.
export function ChatComposer({
  onSend,
  onPick,
  skills,
  busy,
  placeholder = "ask a question, or type / for skills…",
}: {
  onSend: (text: string, file: File | null) => Promise<void>;
  onPick: (target: Skill | "creator") => void;
  skills: Skill[];
  busy: boolean;
  placeholder?: string;
}) {
  const [msg, setMsg] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const slash = msg.startsWith("/") ? msg.slice(1).toLowerCase().trim() : null;
  const showCreator = slash !== null && ("skill-creator".includes(slash) || slash === "");
  const matches = slash !== null ? skills.filter((s) => s.name.toLowerCase().includes(slash)) : [];
  const menuOpen = slash !== null && (showCreator || matches.length > 0);

  const pick = (target: Skill | "creator") => {
    setMsg("");
    onPick(target);
  };

  const submit = async () => {
    const text = msg.trim();
    const cmd = text.startsWith("/") ? text.slice(1).toLowerCase() : null;
    if (cmd !== null) {
      if (["skill-creator", "skill", "new-skill", "create"].includes(cmd)) return pick("creator");
      const m = skills.find(
        (s) => s.name.toLowerCase() === cmd || s.name.toLowerCase().replace(/\s+/g, "-") === cmd,
      );
      if (m) return pick(m);
    }
    if ((!text && !file) || busy) return;
    const staged = file;
    setMsg("");
    setFile(null);
    if (fileRef.current) fileRef.current.value = "";
    await onSend(text, staged);
  };

  return (
    <div className="relative border-t border-line p-3">
      {menuOpen && (
        <div className="absolute bottom-full left-3 mb-1 w-72 overflow-hidden rounded-md border border-line-2 bg-panel-2 p-1 shadow-2xl">
          {showCreator && (
            <Item icon={<Sparkles size={13} className="text-accent" />} onClick={() => pick("creator")}>
              <span className="font-mono">/skill-creator</span>
              <span className="ml-auto text-[10px] text-faint">make a new skill</span>
            </Item>
          )}
          {matches.map((s) => (
            <Item key={s.id} icon={<Boxes size={13} className="text-faint" />} onClick={() => pick(s)}>
              {s.name}
            </Item>
          ))}
        </div>
      )}
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
          placeholder={file ? "say 'ingest it' to add this file…" : placeholder}
          className="flex-1 rounded-md border border-line bg-bg px-3 py-2.5 text-sm text-fg outline-none placeholder:text-faint focus:border-line-2"
        />
        <Button type="submit" disabled={busy}>
          <CornerDownLeft size={14} /> Send
        </Button>
      </form>
    </div>
  );
}

function Item({
  icon,
  onClick,
  children,
}: {
  icon: React.ReactNode;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm text-muted transition-colors hover:bg-panel hover:text-fg"
    >
      {icon}
      <span className="flex min-w-0 flex-1 items-center gap-2 truncate">{children}</span>
    </button>
  );
}
