// Typed client for the AdaRag FastAPI backend, reached through the /api proxy (see next.config).

const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store", ...init });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${init?.method ?? "GET"} ${path} -> ${res.status} ${detail.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

export interface Citation {
  n: number;
  source: string;
  chunk_id: string;
  score: number;
  modality: string;
  original_path: string | null;
}

export interface Answer {
  answer: string;
  citations: Citation[];
  search_query?: string;
}

export interface IngestResult {
  document_id: string;
  chunks: number;
  source: string;
}

export interface DocumentInfo {
  source: string;
  modality: string;
  original_path: string | null;
  chunks: number;
}

// Answer-time overrides carried by an applied skill (persona framing + retrieval depth).
export interface SkillOverride {
  persona?: string;
  top_k?: number;
}

// A chat "mode": a provider+model combo to switch the LLM for a request.
export interface ModeOption {
  provider: string;
  model: string;
}

export interface TrialPoint {
  k: number;
  ndcg: number;
  ms: number;
}

export interface StudyState {
  status: "idle" | "starting" | "building_queries" | "running" | "done" | "error";
  bucket?: string;
  queries?: number;
  trials_done?: number;
  trials_total?: number;
  trials?: TrialPoint[];
  baseline?: TrialPoint;
  front?: TrialPoint[];
  headline?: string;
  error?: string;
}

function json(body: unknown): RequestInit {
  return { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) };
}

// Download a preserved original with its real filename. Fetches to a blob so the name is exact
// (not derived from the URL) and a missing file surfaces as an error instead of saving junk.
export async function downloadFile(path: string, name: string): Promise<void> {
  const res = await fetch(`${BASE}/files/raw?path=${encodeURIComponent(path)}`, { cache: "no-store" });
  if (!res.ok) throw new Error(res.status === 404 ? "original no longer stored" : `failed (${res.status})`);
  const obj = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = obj;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(obj);
}

export const api = {
  health: () => req<{ status: string; services: Record<string, boolean> }>("/health"),
  listBuckets: () => req<{ buckets: string[] }>("/buckets"),
  listDocuments: (bucket = "default") =>
    req<{ documents: DocumentInfo[] }>(`/documents?bucket=${encodeURIComponent(bucket)}`),
  deleteDocument: (bucket: string, source: string) =>
    req<{ bucket: string; source: string; status: string }>(
      `/documents?source=${encodeURIComponent(source)}&bucket=${encodeURIComponent(bucket)}`,
      { method: "DELETE" },
    ),
  // A direct URL to a preserved original (for <img>/<audio>/<video> or a download link).
  fileUrl: (path: string, name?: string) =>
    `${BASE}/files/raw?path=${encodeURIComponent(path)}${name ? `&name=${encodeURIComponent(name)}` : ""}`,
  createBucket: (name: string) =>
    req<{ bucket: string; status: string }>(`/buckets/${encodeURIComponent(name)}`, { method: "POST" }),
  deleteBucket: (name: string) =>
    req<{ bucket: string; status: string }>(`/buckets/${encodeURIComponent(name)}`, { method: "DELETE" }),
  query: (query: string, bucket = "default", skill?: SkillOverride) =>
    req<Answer>("/query", json({ query, bucket, skill })),
  chat: (sessionId: string, message: string, bucket = "default", mode?: ModeOption) =>
    req<Answer>("/chat", json({ session_id: sessionId, message, bucket, mode })),
  route: (message: string) => req<{ intent: "ingest" | "ask" }>("/route", json({ message })),
  listModes: () => req<{ modes: ModeOption[] }>("/models"),
  optimizeRun: (bucket: string, trials = 20, max_queries = 12) =>
    req<{ started: boolean; running: boolean }>("/optimize/run", json({ bucket, trials, max_queries })),
  optimizeStatus: () => req<StudyState>("/optimize/status"),
  ingest: (file: File, bucket = "default") => {
    const form = new FormData();
    form.append("file", file);
    form.append("bucket", bucket);
    return req<IngestResult>("/ingest", { method: "POST", body: form });
  },
};
