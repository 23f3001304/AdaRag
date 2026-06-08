import { cn } from "@/lib/cn";

/** AdaRag mark: 4x4 dot-grid "A". Apex pair in accent, rest neutral - same glyph as the favicon. */
export function Logo({ size = 22, className }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
      className={cn("shrink-0", className)}
    >
      {/* apex */}
      <rect x="7"  y="1"  width="4" height="4" rx="0.75" className="fill-accent" />
      <rect x="13" y="1"  width="4" height="4" rx="0.75" className="fill-accent" />
      {/* upper legs */}
      <rect x="1"  y="7"  width="4" height="4" rx="0.75" className="fill-fg" />
      <rect x="19" y="7"  width="4" height="4" rx="0.75" className="fill-fg" />
      {/* crossbar */}
      <rect x="1"  y="13" width="4" height="4" rx="0.75" className="fill-fg" />
      <rect x="7"  y="13" width="4" height="4" rx="0.75" className="fill-fg" />
      <rect x="13" y="13" width="4" height="4" rx="0.75" className="fill-fg" />
      <rect x="19" y="13" width="4" height="4" rx="0.75" className="fill-fg" />
      {/* lower legs */}
      <rect x="1"  y="19" width="4" height="4" rx="0.75" className="fill-fg" />
      <rect x="19" y="19" width="4" height="4" rx="0.75" className="fill-fg" />
    </svg>
  );
}
