"use client";

import { Search as SearchIcon } from "lucide-react";
import { useState } from "react";

import { Button, Panel } from "@/components/ui";
import { type Answer, api } from "@/lib/api";
import { cn } from "@/lib/cn";

const MOD_BG: Record<string, string> = {
  text: "bg-mod-text",
  image: "bg-mod-image",
  audio: "bg-mod-audio",
  video: "bg-mod-video",
};

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [res, setRes] = useState<Answer | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const run = async () => {
    if (!q.trim() || loading) return;
    setLoading(true);
    setErr("");
    setRes(null);
    try {
      setRes(await api.query(q, "default"));
    } catch (e) {
      setErr(String(e).includes("Failed to fetch") ? "backend offline" : "query failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <div>
        <h2 className="font-display text-2xl font-bold tracking-tight text-fg">Search</h2>
        <p className="mt-1.5 text-sm text-muted">
          Ask a question; see the answer and the exact chunks it was grounded in.
        </p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          run();
        }}
        className="flex gap-2"
      >
        <div className="flex flex-1 items-center gap-2.5 rounded-md border border-line bg-panel px-3 focus-within:border-line-2">
          <SearchIcon size={16} className="shrink-0 text-faint" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="how does bge-m3 produce sparse vectors?"
            className="flex-1 bg-transparent py-2.5 text-sm text-fg outline-none placeholder:text-faint"
          />
        </div>
        <Button type="submit" disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </Button>
      </form>

      {err && <Panel className="px-5 py-4 text-sm text-danger">{err}</Panel>}

      {res && (
        <div className="flex flex-col gap-5">
          <Panel className="px-6 py-5">
            <span className="font-mono text-[10px] uppercase tracking-wider text-faint">answer</span>
            <p className="mt-2.5 whitespace-pre-wrap text-sm leading-relaxed text-fg">{res.answer}</p>
          </Panel>
          <div>
            <span className="font-mono text-[10px] uppercase tracking-wider text-faint">
              retrieval trace · {res.citations.length} chunks
            </span>
            <div className="mt-2.5 flex flex-col gap-1.5">
              {res.citations.map((c) => (
                <div
                  key={c.chunk_id}
                  className="flex items-center gap-3 rounded-md border border-line bg-panel px-4 py-2.5"
                >
                  <span className="font-mono text-xs text-faint">[{c.n}]</span>
                  <span className={cn("size-1.5 shrink-0 rounded-full", MOD_BG[c.modality] ?? MOD_BG.text)} />
                  <span className="truncate font-mono text-sm text-fg">{c.source}</span>
                  <span className="ml-auto font-mono text-[11px] text-muted">{c.modality}</span>
                  <div className="h-1 w-16 overflow-hidden rounded-full bg-panel-2">
                    <div className="h-full bg-accent" style={{ width: `${Math.round(c.score * 100)}%` }} />
                  </div>
                  <span className="w-9 text-right font-mono text-xs tabular-nums text-muted">
                    {c.score.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
