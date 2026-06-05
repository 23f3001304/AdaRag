import type { ButtonHTMLAttributes, HTMLAttributes } from "react";

import { cn } from "@/lib/cn";

const button = {
  primary: "bg-accent text-accent-ink hover:bg-accent-2 font-medium",
  outline: "border border-line-2 text-fg hover:bg-panel-2",
  ghost: "text-muted hover:text-fg hover:bg-panel",
  danger: "border border-line-2 text-danger hover:bg-panel-2",
} as const;

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof button }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md px-3 py-1.5 text-sm",
        "transition-colors disabled:pointer-events-none disabled:opacity-40",
        button[variant],
        className,
      )}
      {...props}
    />
  );
}

export function Panel({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-lg border border-line bg-panel", className)} {...props} />;
}

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border border-line px-1.5 py-px",
        "font-mono text-[11px] uppercase tracking-wider text-muted",
        className,
      )}
      {...props}
    />
  );
}

/** A label/value pair rendered in mono - used for scores, counts, costs. */
export function Stat({ label, value, className }: { label: string; value: string; className?: string }) {
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <span className="font-mono text-[11px] uppercase tracking-wider text-faint">{label}</span>
      <span className="font-mono text-2xl font-medium text-fg tabular-nums">{value}</span>
    </div>
  );
}
