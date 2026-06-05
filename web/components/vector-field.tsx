"use client";

import { motion } from "motion/react";
import { useMemo, useState } from "react";

const MOD: Record<string, string> = {
  text: "#6aa6ff",
  image: "#f5b342",
  audio: "#34d3bd",
  video: "#fb7185",
};

interface Pt {
  x: number;
  y: number;
  i: number;
  score: number;
}

/** A phyllotaxis cluster + a sparse k-nearest-neighbor edge list, both deterministic. */
function build(n: number): { pts: Pt[]; edges: [number, number][] } {
  const pts: Pt[] = Array.from({ length: n }, (_, i) => {
    const a = i * 2.399963;
    const r = 8 + 37 * Math.sqrt((i + 0.5) / n);
    return { x: 50 + Math.cos(a) * r, y: 50 + Math.sin(a) * r, i, score: 0.58 + 0.4 * (1 - r / 45) };
  });
  const edges: [number, number][] = [];
  for (const p of pts) {
    const near = pts
      .filter((q) => q.i !== p.i)
      .sort((a, b) => Math.hypot(p.x - a.x, p.y - a.y) - Math.hypot(p.x - b.x, p.y - b.y))
      .slice(0, 2);
    for (const q of near) if (p.i < q.i) edges.push([p.i, q.i]);
  }
  return { pts, edges };
}

export function VectorField({
  count,
  modality,
  active,
}: {
  count: number;
  modality: string;
  active: boolean;
}) {
  const n = Math.min(count, 44);
  const { pts, edges } = useMemo(() => build(n), [n]);
  const [hover, setHover] = useState<number | null>(null);
  const color = MOD[modality] ?? MOD.text;
  const hoverEdges = hover === null ? [] : edges.filter(([a, b]) => a === hover || b === hover);

  return (
    <div className="flex flex-1 flex-col gap-2">
      <svg viewBox="0 0 100 100" className="h-[230px] w-full overflow-visible">
        {active &&
          edges.map(([a, b], k) => (
            <line
              key={k}
              x1={pts[a].x}
              y1={pts[a].y}
              x2={pts[b].x}
              y2={pts[b].y}
              stroke={color}
              strokeWidth={0.18}
              strokeOpacity={0.1}
            />
          ))}
        {active &&
          pts.map((p) => (
            <motion.circle
              key={p.i}
              r={1.7}
              fill={color}
              initial={{ cx: 50, cy: 50, opacity: 0 }}
              animate={{ cx: p.x, cy: p.y, opacity: 0.62 }}
              transition={{ delay: p.i * 0.02, type: "spring", stiffness: 55, damping: 13 }}
            />
          ))}
        {active && hover !== null && (
          <g>
            {hoverEdges.map(([a, b], k) => (
              <line
                key={k}
                x1={pts[a].x}
                y1={pts[a].y}
                x2={pts[b].x}
                y2={pts[b].y}
                stroke={color}
                strokeWidth={0.5}
                strokeOpacity={0.75}
              />
            ))}
            <circle
              cx={pts[hover].x}
              cy={pts[hover].y}
              r={3.6}
              fill="none"
              stroke={color}
              strokeWidth={0.5}
              strokeOpacity={0.85}
            />
            <circle cx={pts[hover].x} cy={pts[hover].y} r={2.1} fill={color} />
          </g>
        )}
        {active &&
          pts.map((p) => (
            <circle
              key={`hit-${p.i}`}
              cx={p.x}
              cy={p.y}
              r={3.6}
              fill="transparent"
              className="cursor-pointer"
              onMouseEnter={() => setHover(p.i)}
              onMouseLeave={() => setHover((h) => (h === p.i ? null : h))}
            />
          ))}
      </svg>
      <div className="font-mono text-[11px] text-faint">
        {hover !== null ? (
          <span className="text-muted">
            chunk <span className="text-fg">{hover}</span> · {modality} · sim{" "}
            <span className="text-fg">{pts[hover].score.toFixed(2)}</span>
          </span>
        ) : active ? (
          `${n} vectors · hover to inspect`
        ) : (
          "awaiting embeddings"
        )}
      </div>
    </div>
  );
}
