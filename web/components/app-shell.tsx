"use client";

import {
  Boxes,
  LayoutGrid,
  MessageSquare,
  Search,
  SlidersHorizontal,
  Upload,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentType } from "react";

import { cn } from "@/lib/cn";
import { Logo } from "@/components/logo";

type NavItem = { href: string; label: string; icon: ComponentType<{ size?: number }>; soon?: boolean };

const NAV: NavItem[] = [
  { href: "/", label: "Overview", icon: LayoutGrid },
  { href: "/ingest", label: "Ingest", icon: Upload },
  { href: "/search", label: "Search", icon: Search, soon: true },
  { href: "/chat", label: "Chat", icon: MessageSquare, soon: true },
  { href: "/skills", label: "Skills", icon: Boxes, soon: true },
  { href: "/optimizer", label: "Optimizer", icon: SlidersHorizontal, soon: true },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const active = NAV.find((n) => n.href === pathname) ?? NAV[0];

  return (
    <div className="grid min-h-screen grid-cols-[244px_1fr]">
      <aside className="flex flex-col border-r border-line bg-bg/60">
        <div className="flex h-14 items-center gap-2.5 border-b border-line px-5">
          <Logo size={20} />
          <span className="font-display text-[15px] font-bold tracking-tight">AdaRag</span>
          <span className="ml-auto font-mono text-[10px] uppercase tracking-wider text-faint">
            strata
          </span>
        </div>

        <div className="px-3 py-3">
          <button className="flex w-full items-center justify-between rounded-md border border-line bg-panel px-2.5 py-2 text-left hover:border-line-2">
            <span className="flex flex-col">
              <span className="font-mono text-[10px] uppercase tracking-wider text-faint">bucket</span>
              <span className="text-sm text-fg">default</span>
            </span>
            <span className="font-mono text-xs text-faint">/</span>
          </button>
        </div>

        <nav className="flex flex-1 flex-col gap-0.5 px-3">
          {NAV.map(({ href, label, icon: Icon, soon }) => {
            const isActive = href === active.href;
            return (
              <Link
                key={href}
                href={soon ? "#" : href}
                aria-disabled={soon}
                className={cn(
                  "group flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm transition-colors",
                  isActive ? "bg-panel text-fg" : "text-muted hover:bg-panel hover:text-fg",
                  soon && "pointer-events-none opacity-45",
                )}
              >
                <Icon size={16} />
                <span>{label}</span>
                {isActive && <span className="ml-auto h-3.5 w-0.5 rounded-full bg-accent" />}
                {soon && (
                  <span className="ml-auto font-mono text-[9px] uppercase tracking-wider text-faint">
                    soon
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2 border-t border-line px-5 py-3">
          <span className="size-1.5 rounded-full bg-accent" />
          <span className="font-mono text-[11px] text-muted">backend on :8000</span>
        </div>
      </aside>

      <div className="flex min-h-screen flex-col">
        <header className="flex h-14 items-center gap-3 border-b border-line px-7">
          <h1 className="text-sm font-medium text-fg">{active.label}</h1>
          <span className="font-mono text-xs text-faint">/ {active.href}</span>
        </header>
        <main className="flex-1 overflow-y-auto px-7 py-7">{children}</main>
      </div>
    </div>
  );
}
