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

function json(body: unknown): RequestInit {
  return { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) };
}

export const api = {
  health: () => req<{ status: string; services: Record<string, boolean> }>("/health"),
  listBuckets: () => req<{ buckets: string[] }>("/buckets"),
  listDocuments: (bucket = "default") =>
    req<{ documents: DocumentInfo[] }>(`/documents?bucket=${encodeURIComponent(bucket)}`),
  createBucket: (name: string) =>
    req<{ bucket: string; status: string }>(`/buckets/${encodeURIComponent(name)}`, { method: "POST" }),
  deleteBucket: (name: string) =>
    req<{ bucket: string; status: string }>(`/buckets/${encodeURIComponent(name)}`, { method: "DELETE" }),
  query: (query: string, bucket = "default", skill?: SkillOverride) =>
    req<Answer>("/query", json({ query, bucket, skill })),
  chat: (sessionId: string, message: string, bucket = "default", skill?: SkillOverride) =>
    req<Answer>("/chat", json({ session_id: sessionId, message, bucket, skill })),
  ingest: (file: File, bucket = "default") => {
    const form = new FormData();
    form.append("file", file);
    form.append("bucket", bucket);
    return req<IngestResult>("/ingest", { method: "POST", body: form });
  },
};
