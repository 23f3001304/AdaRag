"use client";

import {
  Boxes,
  ChevronRight,
  FileStack,
  LayoutGrid,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  SlidersHorizontal,
  Upload,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ComponentType, useEffect, useState } from "react";

import { BucketSwitcher } from "@/components/bucket-switcher";
import { Logo } from "@/components/logo";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";

type NavItem = { href: string; label: string; icon: ComponentType<{ size?: number }>; soon?: boolean };

const NAV: NavItem[] = [
  { href: "/", label: "Overview", icon: LayoutGrid },
  { href: "/ingest", label: "Ingest", icon: Upload },
  { href: "/files", label: "Files", icon: FileStack },
  { href: "/search", label: "Search", icon: Search },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/skills", label: "Skills", icon: Boxes },
  { href: "/optimizer", label: "Optimizer", icon: SlidersHorizontal },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);
  const active = NAV.find((n) => n.href === pathname) ?? NAV[0];

  useEffect(() => {
    let live = true;
    const ping = () =>
      api
        .health()
        .then((h) => live && setOnline(h.status === "ok"))
        .catch(() => live && setOnline(false));
    ping();
    const id = setInterval(ping, 8000);
    return () => {
      live = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div
      className={cn(
        "grid min-h-screen transition-[grid-template-columns] duration-200",
        collapsed ? "grid-cols-[64px_1fr]" : "grid-cols-[244px_1fr]",
      )}
    >
      <aside className="flex min-w-0 flex-col border-r border-line">
        <div className="flex h-14 items-center gap-2.5 border-b border-line px-4">
          <Logo size={20} />
          {!collapsed && (
            <>
              <span className="font-display text-[15px] font-bold tracking-tight">AdaRag</span>
              <span className="ml-auto font-mono text-[10px] uppercase tracking-wider text-faint">
                strata
              </span>
            </>
          )}
        </div>

        <div className="p-2.5">
          <BucketSwitcher collapsed={collapsed} />
        </div>

        <nav className="flex flex-1 flex-col gap-0.5 px-2.5">
          {NAV.map(({ href, label, icon: Icon, soon }) => {
            const isActive = href === active.href;
            return (
              <Link
                key={href}
                href={soon ? "#" : href}
                title={collapsed ? label : undefined}
                aria-disabled={soon}
                className={cn(
                  "group relative flex items-center gap-2.5 rounded-md py-2 text-sm transition-colors",
                  collapsed ? "justify-center px-0" : "px-2.5",
                  isActive ? "bg-panel text-fg" : "text-muted hover:bg-panel hover:text-fg",
                  soon && "pointer-events-none opacity-40",
                )}
              >
                {isActive && (
                  <span className="absolute left-0 h-4 w-0.5 rounded-r-full bg-accent" />
                )}
                <Icon size={16} />
                {!collapsed && <span>{label}</span>}
                {!collapsed && soon && (
                  <span className="ml-auto font-mono text-[9px] uppercase tracking-wider text-faint">
                    soon
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        <div
          className={cn(
            "flex border-t border-line p-2.5",
            collapsed ? "flex-col items-center gap-2.5" : "items-center justify-between",
          )}
        >
          <span
            className="flex items-center gap-2"
            title={
              online ? "backend online" : online === false ? "backend offline" : "checking backend"
            }
          >
            <span
              className={cn(
                "size-1.5 shrink-0 rounded-full transition-colors",
                online ? "bg-accent" : online === false ? "bg-danger" : "bg-faint",
              )}
            />
            {!collapsed && (
              <span className="font-mono text-[11px] text-muted">
                {online ? "backend online" : online === false ? "backend offline" : "checking…"}
              </span>
            )}
          </span>
          <button
            onClick={() => setCollapsed((c) => !c)}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="rounded-md p-1 text-muted transition-colors hover:bg-panel hover:text-fg"
          >
            {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
          </button>
        </div>
      </aside>

      <div className="flex min-h-screen min-w-0 flex-col">
        <header className="flex h-14 items-center gap-2.5 border-b border-line px-7">
          <Link
            href="/"
            className="rounded font-mono text-xs text-faint transition-colors hover:text-fg"
          >
            AdaRag
          </Link>
          <ChevronRight size={13} className="text-faint" />
          <Link
            href={active.href}
            className="text-sm font-medium text-fg transition-colors hover:text-accent"
          >
            {active.label}
          </Link>
        </header>
        <main className="flex-1 overflow-y-auto px-7 py-7">{children}</main>
      </div>
    </div>
  );
}
