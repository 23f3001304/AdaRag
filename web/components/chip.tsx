"use client";

import { Boxes, X } from "lucide-react";

// A small dismissable chip used in the chat header for the active skill / "creating skill" hint.
export function Chip({ children, onClear }: { children: React.ReactNode; onClear: () => void }) {
  return (
    <span className="flex items-center gap-1 rounded border border-accent/40 bg-accent/10 px-2 py-1 text-xs text-accent">
      <Boxes size={11} />
      <span className="max-w-32 truncate">{children}</span>
      <button onClick={onClear} className="transition-colors hover:text-fg">
        <X size={11} />
      </button>
    </span>
  );
}
