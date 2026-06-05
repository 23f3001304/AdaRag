// A skill bundles a bucket, a persona, retrieval settings, and prompt templates into a reusable
// assistant. Stored client-side for now; the Skills page edits these and Chat applies them.

export interface Skill {
  id: string;
  name: string;
  bucket: string;
  persona: string;
  topK: number;
  rerank: number;
  enrich: boolean;
  templates: string[];
}

const KEY = "adarag.skills";

export function loadSkills(): Skill[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "[]");
  } catch {
    return [];
  }
}

export function saveSkills(skills: Skill[]): void {
  localStorage.setItem(KEY, JSON.stringify(skills));
}
