"use client";

import { useState } from "react";

import { Panel, Stat } from "@/components/ui";
import { cn } from "@/lib/cn";

type Point = { k: number; ndcg: number; ms: number; tag?: "default" | "knee" | "peak" };

const FRONT: Point[] = [
  { k: 8, ndcg: 0.187, ms: 87 },
  { k: 11, ndcg: 0.19, ms: 97 },
  { k: 12, ndcg: 0.195, ms: 99 },
  { k: 16, ndcg: 0.202, ms: 113 },
  { k: 20, ndcg: 0.234, ms: 144, tag: "default" },
  { k: 23, ndcg: 0.246, ms: 148 },
  { k: 24, ndcg: 0.25, ms: 155 },
  { k: 27, ndcg: 0.26, ms: 169 },
  { k: 32, ndcg: 0.264, ms: 193 },
  { k: 36, ndcg: 0.273, ms: 225, tag: "knee" },
  { k: 39, ndcg: 0.276, ms: 237 },
  { k: 42, ndcg: 0.278, ms: 252, tag: "peak" },
];

const W = 560;
const H = 300;
const PAD = 46;
const xs = (ms: number) => PAD + ((ms - 75) / (265 - 75)) * (W - PAD - 18);
const ys = (n: number) => H - PAD - ((n - 0.175) / (0.29 - 0.175)) * (H - PAD - 18);

export default function OptimizerPage() {
  const [hi, setHi] = useState<Point | null>(null);
  const path = FRONT.map((p, i) => `${i ? "L" : "M"}${xs(p.ms).toFixed(1)},${ys(p.ndcg).toFixed(1)}`).join(" ");

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <div>
        <h2 className="font-display text-2xl font-bold tracking-tight text-fg">Optimizer</h2>
        <p className="mt-1.5 max-w-xl text-sm text-muted">
          An Optuna study maps the relevance/latency frontier over rerank_candidates and finds the
          diminishing-returns knee. Local GPU, free trials.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_220px]">
        <Panel className="px-5 py-5">
          <span className="font-mono text-[10px] uppercase tracking-wider text-faint">
            pareto front · nDCG vs latency
          </span>
          <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 w-full">
            {[0.2, 0.24, 0.28].map((n) => (
              <g key={n}>
                <line x1={PAD} y1={ys(n)} x2={W - 18} y2={ys(n)} stroke="var(--color-line)" strokeWidth={1} />
                <text x={PAD - 8} y={ys(n) + 3} textAnchor="end" className="fill-faint font-mono text-[10px]">
                  {n.toFixed(2)}
                </text>
              </g>
            ))}
            {[100, 150, 200, 250].map((ms) => (
              <text key={ms} x={xs(ms)} y={H - PAD + 16} textAnchor="middle" className="fill-faint font-mono text-[10px]">
                {ms}ms
              </text>
            ))}
            <path d={path} fill="none" stroke="var(--color-line-2)" strokeWidth={1.5} />
            {FRONT.map((p) => (
              <g
                key={p.k}
                className="cursor-pointer"
                onMouseEnter={() => setHi(p)}
                onMouseLeave={() => setHi(null)}
              >
                <circle
                  cx={xs(p.ms)}
                  cy={ys(p.ndcg)}
                  r={p.tag === "knee" ? 5 : hi?.k === p.k ? 4.5 : 3.4}
                  className={cn(
                    p.tag === "knee"
                      ? "fill-accent"
                      : p.tag === "default"
                        ? "fill-fg"
                        : "fill-muted",
                  )}
                />
                {p.tag && (
                  <text
                    x={xs(p.ms)}
                    y={ys(p.ndcg) - 10}
                    textAnchor="middle"
                    className="fill-faint font-mono text-[9px] uppercase"
                  >
                    {p.tag}
                  </text>
                )}
              </g>
            ))}
          </svg>
          <div className="h-4 font-mono text-[11px] text-muted">
            {hi && (
              <span>
                K={hi.k} · nDCG <span className="text-fg">{hi.ndcg.toFixed(3)}</span> ·{" "}
                <span className="text-fg">{hi.ms}ms</span>
              </span>
            )}
          </div>
        </Panel>

        <div className="flex flex-col gap-4">
          <Panel className="px-5 py-4">
            <span className="font-mono text-[10px] uppercase tracking-wider text-faint">headline</span>
            <p className="mt-2 text-sm leading-relaxed text-fg">
              K=36 holds <span className="text-accent">98% of peak nDCG</span> at{" "}
              <span className="text-accent">~11% lower latency</span> than maxing the pool. The default
              K=20 already sits on the efficient frontier.
            </p>
          </Panel>
          <Panel className="grid grid-cols-2 gap-5 px-5 py-4">
            <Stat label="default" value="K=20" />
            <Stat label="efficient" value="K=36" />
            <Stat label="trials" value="25" />
            <Stat label="cost" value="$0" />
          </Panel>
        </div>
      </div>
    </div>
  );
}
