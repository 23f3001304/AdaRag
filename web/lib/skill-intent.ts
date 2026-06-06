// Skill-creation intent detection. The model is the arbiter, but a cheap client heuristic gates
// the round-trip so questions and lookups (the bulk of messages) skip the LLM call entirely. Only
// plausibly-skill messages pay the latency. Returns true ONLY when both heuristic and LLM agree.

import { api } from "@/lib/api";

const QUESTION_STARTERS = new Set([
  "what", "who", "where", "when", "how", "why", "is", "are", "do", "does", "did",
  "can", "could", "should", "would", "will", "tell", "list", "show", "find", "explain",
  "summarize", "describe", "give", "compare", "search", "look", "name",
]);

// Imperatives that signal "I want something built". Must co-occur with an assistant-shaped noun.
const WANT = /\b(make|create|build|design|i\s+want|i\s+need|need\s+(?:a|an)|give\s+me|set\s+up)\b/;

// The noun being built - what makes the request actually about creating an assistant.
const NOUN = /\b(skill|assistant|persona|expert|analyst|reviewer|critic|coach|tutor|agent|bot|helper|character)\b/;

function looksLikeSkillRequest(text: string): boolean {
  const t = text.trim().toLowerCase();
  if (t.length < 8 || t.startsWith("/") || t.endsWith("?")) return false;
  if (QUESTION_STARTERS.has(t.split(/\s+/)[0])) return false;
  return WANT.test(t) && NOUN.test(t);
}

// True only when the heuristic flags + the LLM confirms. Falls back to "no" on any error.
export async function isSkillRequest(text: string): Promise<boolean> {
  if (!looksLikeSkillRequest(text)) return false;
  const r = await api.routeSkill(text).catch(() => ({ intent: "ask" as const }));
  return r.intent === "skill";
}
