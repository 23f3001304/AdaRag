"use client";

import { Boxes, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Button, Panel } from "@/components/ui";
import { loadSkills, saveSkills, type Skill } from "@/lib/skills";

const input =
  "w-full rounded-md border border-line bg-bg px-2.5 py-2 text-sm text-fg outline-none placeholder:text-faint focus:border-line-2";

const blank = (): Skill => ({
  id: crypto.randomUUID(),
  name: "",
  bucket: "default",
  persona: "",
  topK: 5,
  rerank: 20,
  enrich: true,
  templates: [],
});

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [draft, setDraft] = useState<Skill | null>(null);

  useEffect(() => {
    setSkills(loadSkills());
  }, []);

  const persist = (next: Skill[]) => {
    setSkills(next);
    saveSkills(next);
  };
  const save = () => {
    if (!draft || !draft.name.trim()) return;
    const has = skills.some((s) => s.id === draft.id);
    persist(has ? skills.map((s) => (s.id === draft.id ? draft : s)) : [...skills, draft]);
    setDraft(null);
  };

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="font-display text-2xl font-bold tracking-tight text-fg">Skills</h2>
          <p className="mt-1.5 max-w-xl text-sm text-muted">
            A skill bundles a bucket, a persona, retrieval settings, and prompt templates into a
            reusable assistant. Stored locally for now.
          </p>
        </div>
        <Button onClick={() => setDraft(blank())}>
          <Plus size={14} /> New skill
        </Button>
      </div>

      {draft && (
        <Panel className="flex flex-col gap-4 px-6 py-5">
          <div className="grid grid-cols-2 gap-4">
            <Field label="name">
              <input
                value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                placeholder="Support assistant"
                className={input}
              />
            </Field>
            <Field label="bucket">
              <input
                value={draft.bucket}
                onChange={(e) => setDraft({ ...draft, bucket: e.target.value })}
                className={input}
              />
            </Field>
          </div>
          <Field label="persona / system prompt">
            <textarea
              value={draft.persona}
              onChange={(e) => setDraft({ ...draft, persona: e.target.value })}
              rows={2}
              placeholder="Answer as a concise support engineer; cite sources."
              className={input}
            />
          </Field>
          <div className="grid grid-cols-3 gap-4">
            <Field label="top_k">
              <input
                type="number"
                value={draft.topK}
                onChange={(e) => setDraft({ ...draft, topK: +e.target.value })}
                className={input}
              />
            </Field>
            <Field label="rerank">
              <input
                type="number"
                value={draft.rerank}
                onChange={(e) => setDraft({ ...draft, rerank: +e.target.value })}
                className={input}
              />
            </Field>
            <Field label="enrich">
              <label className="flex items-center gap-2 py-2 text-sm text-fg">
                <input
                  type="checkbox"
                  checked={draft.enrich}
                  onChange={(e) => setDraft({ ...draft, enrich: e.target.checked })}
                  className="accent-accent"
                />
                contextual
              </label>
            </Field>
          </div>
          <Field label="prompt templates (one per line)">
            <textarea
              value={draft.templates.join("\n")}
              onChange={(e) =>
                setDraft({ ...draft, templates: e.target.value.split("\n").filter(Boolean) })
              }
              rows={3}
              placeholder={"Summarize {topic}\nCompare {a} and {b}"}
              className={input}
            />
          </Field>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setDraft(null)}>
              Cancel
            </Button>
            <Button onClick={save}>Save skill</Button>
          </div>
        </Panel>
      )}

      {skills.length === 0 && !draft ? (
        <Panel className="px-5 py-10 text-center text-sm text-muted">
          No skills yet. Create one to bundle a bucket, a persona, and a retrieval config.
        </Panel>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {skills.map((s) => (
            <Panel key={s.id} className="flex flex-col gap-3 px-5 py-4">
              <div className="flex items-start gap-2.5">
                <Boxes size={16} className="mt-0.5 shrink-0 text-accent" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-fg">{s.name}</p>
                  <p className="truncate font-mono text-[11px] text-faint">bucket: {s.bucket}</p>
                </div>
                <button
                  onClick={() => persist(skills.filter((x) => x.id !== s.id))}
                  className="text-faint transition-colors hover:text-danger"
                >
                  <Trash2 size={14} />
                </button>
              </div>
              {s.persona && <p className="line-clamp-2 text-xs text-muted">{s.persona}</p>}
              <div className="flex flex-wrap gap-1.5">
                <Tag>top_k {s.topK}</Tag>
                <Tag>rerank {s.rerank}</Tag>
                {s.enrich && <Tag>enrich</Tag>}
                {s.templates.length > 0 && <Tag>{s.templates.length} templates</Tag>}
              </div>
              <button
                onClick={() => setDraft(s)}
                className="self-start font-mono text-[11px] text-accent hover:underline"
              >
                edit
              </button>
            </Panel>
          ))}
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="font-mono text-[10px] uppercase tracking-wider text-faint">{label}</span>
      {children}
    </label>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded border border-line px-1.5 py-px font-mono text-[10px] text-muted">
      {children}
    </span>
  );
}
