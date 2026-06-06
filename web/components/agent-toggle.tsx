"use client";

import { Zap } from "lucide-react";

import { cn } from "@/lib/cn";

// Per-chat agent-mode toggle. Off = normal RAG answers. On = the model can request tool use that
// the user approves inline (slice 2B wires this to claude-cli's --permission-prompt-tool).
export function AgentToggle({ on, onToggle }: { on: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      title={on ? "Agent mode on - the model can request tool use" : "Turn on agent mode"}
      className={cn(
        "flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs transition-colors",
        on
          ? "border-accent/60 bg-accent/15 text-accent"
          : "border-line text-muted hover:border-line-2 hover:text-fg",
      )}
    >
      <Zap size={11} className={on ? "fill-accent" : ""} />
      agent
    </button>
  );
}
