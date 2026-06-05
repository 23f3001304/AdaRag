"use client";

import { Loader2, Play } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useBucket } from "@/components/bucket-context";
import { Button, Panel, Stat } from "@/components/ui";
import { type StudyState, type TrialPoint, api } from "@/lib/api";

// A sample study (the phase-5 corpus) so the page reads well before you run one on your bucket.
const DEMO: TrialPoint[] = [
  { k: 8, ndcg: 0.187, ms: 87 }, { k: 11, ndcg: 0.19, ms: 97 }, { k: 12, ndcg: 0.195, ms: 99 },
  { k: 16, ndcg: 0.202, ms: 113 }, { k: 20, ndcg: 0.234, ms: 144 }, { k: 23, ndcg: 0.246, ms: 148 },
  { k: 24, ndcg: 0.25, ms: 155 }, { k: 27, ndcg: 0.26, ms: 169 }, { k: 32, ndcg: 0.264, ms: 193 },
  { k: 36, ndcg: 0.273, ms: 225 }, { k: 39, ndcg: 0.276, ms: 237 }, { k: 42, ndcg: 0.278, ms: 252 },
];
const DEMO_HEADLINE =
  "Sample study (phase-5 corpus): K=36 holds ~98% of peak nDCG at ~11% lower latency than maxing the pool. Run one on your bucket.";
const RUNNING = new Set(["starting", "building_queries", "running"]);

export default function OptimizerPage() {
  const { bucket } = useBucket();
  const [state, setState] = useState<StudyState | null>(null);
  const [starting, setStarting] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const poll = useCallback(() => {
    api
      .optimizeStatus()
      .then((s) => {
        setState(s);
        if (RUNNING.has(s.status)) timer.current = setTimeout(poll, 1500);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    poll(); // pick up a study already in progress
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [poll]);

  const run = async () => {
    setStarting(true);
    try {
      await api.optimizeRun(bucket, 20, 12);
      poll();
    } catch {
      /* the status poll surfaces any failure */
    } finally {
      setStarting(false);
    }
  };

  // Only treat the (global) study state as ours when it's for the bucket we're viewing.
  const mine = state && state.bucket === bucket ? state : null;
  const running = (mine ? RUNNING.has(mine.status) : false) || starting;
  const done = mine?.status === "done";
  const live = mine?.trials?.length ? mine.trials : null;
  // Plot the Pareto front when done (a clean frontier), the accumulating trials while running, else
  // the sample. Dominated trial points are not drawn.
  const plot = done ? (mine?.front ?? []) : (live ?? DEMO);
  const showLine = done || !live;
  const headline = done ? mine?.headline : !mine || mine.status === "idle" ? DEMO_HEADLINE : null;

  const ms = plot.map((p) => p.ms);
  const nd = plot.map((p) => p.ndcg);
  const xDomain = [
    Math.floor((Math.min(...ms) - 8) / 10) * 10,
    Math.ceil((Math.max(...ms) + 8) / 10) * 10,
  ];
  const yLo = Math.max(0, Math.floor((Math.min(...nd) - 0.03) * 20) / 20);
  const yHi = Math.min(1, Math.ceil((Math.max(...nd) + 0.03) * 20) / 20);
  const yTicks: number[] = [];
  for (let v = yLo; v <= yHi + 1e-9; v += 0.05) yTicks.push(+v.toFixed(2));

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl font-bold tracking-tight text-fg">Optimizer</h2>
          <p className="mt-1.5 max-w-xl text-sm text-muted">
            An Optuna study maps the relevance/latency frontier over rerank_candidates for the{" "}
            <span className="text-fg">{bucket}</span> bucket and finds the diminishing-returns knee.
            Local GPU, free trials.
          </p>
        </div>
        <Button onClick={run} disabled={running}>
          {running ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          {running ? "Running…" : "Run study"}
        </Button>
      </div>

      {mine && RUNNING.has(mine.status) && (
        <Panel className="flex items-center gap-3 px-5 py-3 text-sm text-muted">
          <Loader2 size={14} className="shrink-0 animate-spin text-accent" />
          {mine.status === "building_queries"
            ? `Building golden queries from ${mine.bucket}…`
            : `Trial ${mine.trials_done ?? 0} / ${mine.trials_total ?? 0}${mine.queries ? ` · ${mine.queries} queries` : ""}`}
        </Panel>
      )}
      {mine?.status === "error" && (
        <Panel className="px-5 py-3 text-sm text-danger">Study failed: {mine.error}</Panel>
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_220px]">
        <Panel className="px-5 py-5">
          <span className="font-mono text-[10px] uppercase tracking-wider text-faint">
            pareto front · nDCG vs latency · {done ? mine?.bucket : "sample"}
          </span>
          <ResponsiveContainer width="100%" height={300} className="mt-3">
            <ScatterChart margin={{ top: 10, right: 12, bottom: 4, left: -6 }}>
              <CartesianGrid stroke="var(--color-line)" strokeDasharray="3 3" />
              <XAxis
                type="number"
                dataKey="ms"
                domain={xDomain}
                tickFormatter={(v) => `${Math.round(v)}ms`}
                stroke="var(--color-faint)"
                tick={{ fontSize: 10 }}
                tickLine={false}
              />
              <YAxis
                type="number"
                dataKey="ndcg"
                domain={[yLo, yHi]}
                ticks={yTicks}
                tickFormatter={(v) => v.toFixed(2)}
                stroke="var(--color-faint)"
                tick={{ fontSize: 10 }}
                tickLine={false}
                width={42}
              />
              <Tooltip cursor={{ stroke: "var(--color-line-2)" }} content={<TipBox />} />
              <Scatter
                data={plot}
                fill="var(--color-accent)"
                line={showLine ? { stroke: "var(--color-accent)", strokeWidth: 1.5 } : undefined}
                lineType="joint"
              />
            </ScatterChart>
          </ResponsiveContainer>
        </Panel>

        <div className="flex flex-col gap-4">
          <Panel className="px-5 py-4">
            <span className="font-mono text-[10px] uppercase tracking-wider text-faint">headline</span>
            <p className="mt-2 text-sm leading-relaxed text-fg">
              {headline ?? `Running a fresh study on ${bucket}…`}
            </p>
          </Panel>
          <Panel className="grid grid-cols-2 gap-5 px-5 py-4">
            <Stat label="queries" value={mine?.queries != null ? String(mine.queries) : "—"} />
            <Stat label="trials" value={done ? String(mine.trials_total) : "—"} />
            <Stat label="default K" value={mine?.baseline ? String(mine.baseline.k) : "20"} />
            <Stat label="cost" value="$0" />
          </Panel>
        </div>
      </div>
    </div>
  );
}

function TipBox({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: TrialPoint }>;
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-md border border-line-2 bg-panel px-2.5 py-1.5 font-mono text-[11px] text-fg shadow-xl">
      K={p.k} · nDCG {p.ndcg.toFixed(3)} · {Math.round(p.ms)}ms
    </div>
  );
}
