import { ClarificationPanel } from "@/components/clarification-panel";
import { IngestVisual } from "@/components/ingest-visual";

export default function IngestPage() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-7">
      <div>
        <h2 className="font-display text-2xl font-bold tracking-tight text-fg">Ingest</h2>
        <p className="mt-1.5 max-w-xl text-sm text-muted">
          Drop a document and watch it get profiled, chunked, embedded, and indexed into the
          bucket&apos;s vector space. Text, images, audio, and video all route through the same flow.
        </p>
      </div>
      <ClarificationPanel />
      <IngestVisual />
    </div>
  );
}
