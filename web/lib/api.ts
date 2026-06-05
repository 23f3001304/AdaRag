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
  thinking?: string | null;
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
  original_exists?: boolean;
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

// The host provider config (API keys reported only as set/unset, never by value).
export interface ProviderConfig {
  llm_provider: string;
  llm_model: string;
  vision_provider: string;
  vision_model: string;
  ocr_provider: string;
  claude_cli_path: string;
  gemini_cli_path: string;
  ollama_base_url: string;
  keys: { anthropic: boolean; openai: boolean; openrouter: boolean };
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
  // Revoke late: revoking right after click() can truncate the download (corrupt file) in Chromium.
  setTimeout(() => URL.revokeObjectURL(obj), 60_000);
}

// Dedupe citations to at most 5 distinct sources for the chat's source chips.
export function citationsToSources(
  cits: Citation[],
): { source: string; path: string | null; modality: string }[] {
  const seen = new Set<string>();
  return cits
    .filter((c) => !seen.has(c.source) && seen.add(c.source))
    .slice(0, 5)
    .map((c) => ({ source: c.source, path: c.original_path, modality: c.modality }));
}

export interface StreamHandlers {
  query?: (q: string) => void;
  token: (t: string) => void;
  thinking: (t: string) => void;
  done: (citations: Citation[], searchQuery?: string) => void;
  error?: (msg: string) => void;
}

// Stream a chat turn over SSE, invoking handlers as text/thinking deltas arrive.
export async function chatStream(
  body: {
    session_id: string;
    message: string;
    bucket: string;
    mode?: ModeOption;
    skill?: SkillOverride;
  },
  signal: AbortSignal | undefined,
  on: StreamHandlers,
): Promise<void> {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    signal,
    cache: "no-store",
  });
  if (!res.ok || !res.body) throw new Error(`chat/stream -> ${res.status}`);
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() ?? "";
    for (const part of parts) {
      const at = part.indexOf("data:");
      if (at < 0) continue;
      const ev = JSON.parse(part.slice(part.indexOf("{", at)));
      if (ev.type === "text") on.token(ev.text);
      else if (ev.type === "thinking") on.thinking(ev.text);
      else if (ev.type === "query") on.query?.(ev.text);
      else if (ev.type === "done") on.done(ev.citations ?? [], ev.search_query);
      else if (ev.type === "error") on.error?.(ev.text);
    }
  }
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
  chat: (
    sessionId: string,
    message: string,
    bucket = "default",
    mode?: ModeOption,
    skill?: SkillOverride,
    thinking = false,
    signal?: AbortSignal,
  ) =>
    req<Answer>("/chat", {
      ...json({ session_id: sessionId, message, bucket, mode, skill, thinking }),
      signal,
    }),
  route: (message: string) => req<{ intent: "ingest" | "ask" }>("/route", json({ message })),
  draftSkill: (description: string) =>
    req<{ name: string; persona: string; top_k: number }>("/skills/draft", json({ description })),
  listModes: () => req<{ modes: ModeOption[] }>("/models"),
  optimizeRun: (bucket: string, trials = 20, max_queries = 12) =>
    req<{ started: boolean; running: boolean }>("/optimize/run", json({ bucket, trials, max_queries })),
  optimizeStatus: () => req<StudyState>("/optimize/status"),
  getConfig: () => req<ProviderConfig>("/config"),
  putConfig: (data: Record<string, string>) =>
    req<{ ok: boolean; error?: string; config?: ProviderConfig }>("/config", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(data),
    }),
  ingest: (file: File, bucket = "default") => {
    const form = new FormData();
    form.append("file", file);
    form.append("bucket", bucket);
    return req<IngestResult>("/ingest", { method: "POST", body: form });
  },
};
