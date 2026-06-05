import { FileText, Image as ImageIcon, Music, Video, Zap } from "lucide-react";

import { Panel, Stat } from "@/components/ui";

const INGEST = ["Profile", "Chunk", "Enrich", "Embed", "Index"];
const QUERY = ["Retrieve", "Rerank", "Generate"];

const MODALITIES = [
  { label: "text", icon: FileText, color: "text-mod-text" },
  { label: "image", icon: ImageIcon, color: "text-mod-image" },
  { label: "audio", icon: Music, color: "text-mod-audio" },
  { label: "video", icon: Video, color: "text-mod-video" },
];

export default function Overview() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-7">
      <section className="grid-field relative overflow-hidden rounded-xl border border-line px-8 py-11">
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-accent">
          adaptive multimodal rag
        </p>
        <h2 className="mt-3 max-w-2xl text-[2.6rem] font-light leading-[1.12] tracking-tight text-fg">
          Profile every file, route it to the right pipeline, and{" "}
          <span className="font-semibold">self-tune against cost</span>.
        </h2>
        <p className="mt-5 max-w-xl text-sm leading-relaxed text-muted">
          Hybrid retrieval over text, images, audio, and video. Isolated buckets, a conversational
          orchestrator, and an Optuna optimizer that maps relevance against latency.
        </p>
      </section>

      <Panel className="px-7 py-6">
        <div className="mb-5 flex items-center gap-2">
          <Zap size={14} className="text-accent" />
          <span className="font-mono text-[11px] uppercase tracking-wider text-muted">pipeline</span>
        </div>
        <div className="flex flex-wrap items-center gap-y-3">
          {INGEST.map((s, i) => (
            <Stage key={s} label={s} last={i === INGEST.length - 1} />
          ))}
          <span className="mx-3 font-mono text-[10px] uppercase tracking-wider text-faint">query</span>
          {QUERY.map((s, i) => (
            <Stage key={s} label={s} last={i === QUERY.length - 1} />
          ))}
        </div>
      </Panel>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-[1.25fr_1fr]">
        <Panel className="px-7 py-6">
          <span className="font-mono text-[11px] uppercase tracking-wider text-muted">modalities</span>
          <div className="mt-4 flex flex-col gap-3.5">
            {MODALITIES.map(({ label, icon: Icon, color }) => (
              <div key={label} className="flex items-center gap-3">
                <Icon size={16} className={color} />
                <span className="text-sm capitalize text-fg">{label}</span>
                <span className="ml-auto font-mono text-[11px] text-faint">surrogate + original</span>
              </div>
            ))}
          </div>
        </Panel>
        <Panel className="flex flex-col px-7 py-6">
          <span className="font-mono text-[11px] uppercase tracking-wider text-muted">at a glance</span>
          <div className="mt-5 grid grid-cols-2 gap-6">
            <Stat label="modalities" value="4" />
            <Stat label="pipelines" value="∞" />
            <Stat label="$ / query" value="0.035" />
            <Stat label="latency knee" value="K=36" />
          </div>
        </Panel>
      </div>
    </div>
  );
}

function Stage({ label, last }: { label: string; last: boolean }) {
  return (
    <div className="flex items-center">
      <span className="rounded-md border border-line bg-bg px-2.5 py-1 font-mono text-xs text-fg">
        {label}
      </span>
      {!last && <span className="mx-1 h-px w-5 bg-line-2" />}
    </div>
  );
}
