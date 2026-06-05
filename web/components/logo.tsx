import { cn } from "@/lib/cn";

/** The Strata mark: four offset strata, one lime - geological layers for the codename. */
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
      <rect x="3" y="3" width="18" height="3" rx="1.5" className="fill-faint" />
      <rect x="3" y="9" width="13" height="3" rx="1.5" className="fill-accent" />
      <rect x="8" y="15" width="13" height="3" rx="1.5" className="fill-fg" />
      <rect x="3" y="21" width="8" height="3" rx="1.5" className="fill-muted" />
    </svg>
  );
}
