"use client";

import { HelpCircle } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useClarifications } from "@/components/clarification-context";

// App-wide nudge: when files are waiting to be named and you're not already on Ingest, a card
// slides in from the corner and links straight to the question. Hidden on the Ingest tab itself.
export function ClarificationToast() {
  const { items } = useClarifications();
  const pathname = usePathname();
  const show = items.length > 0 && pathname !== "/ingest";
  const n = items.length;
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 16 }}
          className="fixed bottom-5 right-5 z-50"
        >
          <Link
            href="/ingest"
            className="flex items-center gap-2.5 rounded-lg border border-accent/50 bg-panel px-4 py-3 text-sm shadow-[0_8px_24px_rgba(0,0,0,0.4)] transition-colors hover:border-accent"
          >
            <HelpCircle size={16} className="shrink-0 text-accent" />
            <span className="text-fg">
              {n} file{n === 1 ? "" : "s"} need{n === 1 ? "s" : ""} a name
            </span>
            <span className="font-mono text-[11px] text-accent">answer →</span>
          </Link>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
