"use client";

import { Loader2, Power } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { cn } from "@/lib/cn";

// Shows the host CLI-bridge status and, when it's down, a button to start it (the Docker api
// forwards all LLM/vision work to this bridge, so chat/search need it running).
export function BridgeControl({ collapsed }: { collapsed: boolean }) {
  const [up, setUp] = useState<boolean | null>(null);
  const [starting, setStarting] = useState(false);

  const check = useCallback(() => {
    fetch("/bridge-control", { cache: "no-store" })
      .then((r) => r.json())
      .then((d) => setUp(!!d.running))
      .catch(() => setUp(false));
  }, []);

  useEffect(() => {
    check();
    const id = setInterval(check, 8000);
    return () => clearInterval(id);
  }, [check]);

  const start = async () => {
    setStarting(true);
    try {
      const d = await (await fetch("/bridge-control", { method: "POST" })).json();
      setUp(!!d.running);
    } catch {
      setUp(false);
    } finally {
      setStarting(false);
    }
  };

  const dot = (
    <span
      className={cn(
        "size-1.5 shrink-0 rounded-full transition-colors",
        up ? "bg-accent" : up === false ? "bg-danger" : "bg-faint",
      )}
    />
  );

  if (collapsed) {
    return (
      <span title={up ? "bridge online" : up === false ? "bridge offline" : "checking bridge"}>
        {dot}
      </span>
    );
  }

  return (
    <span className="flex items-center gap-2">
      {dot}
      <span className="font-mono text-[11px] text-muted">
        {up ? "bridge online" : up === false ? "bridge offline" : "checking…"}
      </span>
      {up === false && (
        <button
          onClick={start}
          disabled={starting}
          title="Start the CLI bridge on the host"
          className="ml-0.5 flex items-center gap-1 rounded border border-line px-1.5 py-0.5 font-mono text-[10px] text-faint transition-colors hover:border-accent/50 hover:text-accent disabled:opacity-50"
        >
          {starting ? <Loader2 size={10} className="animate-spin" /> : <Power size={10} />}
          {starting ? "starting" : "start"}
        </button>
      )}
    </span>
  );
}
