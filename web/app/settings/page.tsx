"use client";

import { Loader2, Save } from "lucide-react";
import { useEffect, useState } from "react";

import { Button, Panel } from "@/components/ui";
import { type ModeOption, type ProviderConfig, api } from "@/lib/api";

const LLM_PROVIDERS = ["claude-cli", "gemini-cli", "ollama", "anthropic", "openai", "openrouter"];
const VISION_PROVIDERS = ["claude-cli", "gemini-cli", "ollama"];
const OCR_PROVIDERS = ["easyocr", "none"];
const EDITABLE = [
  "llm_provider",
  "llm_model",
  "vision_provider",
  "vision_model",
  "ocr_provider",
  "claude_cli_path",
  "gemini_cli_path",
  "ollama_base_url",
  "ambiguity_provider",
  "ambiguity_model",
] as const;

const input =
  "w-full rounded-md border border-line bg-bg px-2.5 py-2 text-sm text-fg outline-none placeholder:text-faint focus:border-line-2";

export default function SettingsPage() {
  const [cfg, setCfg] = useState<ProviderConfig | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [keys, setKeys] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [modes, setModes] = useState<ModeOption[]>([]);

  useEffect(() => {
    api
      .getConfig()
      .then((c) => {
        setCfg(c);
        setDraft(Object.fromEntries(EDITABLE.map((f) => [f, c[f]])));
      })
      .catch(() => setResult({ ok: false, msg: "Could not load config - is the bridge running?" }));
    api
      .listModes()
      .then((r) => setModes(r.modes))
      .catch(() => {});
  }, []);

  const set = (k: string, v: string) => setDraft((d) => ({ ...d, [k]: v }));
  const modelsFor = (p: string) => [...new Set(modes.filter((m) => m.provider === p).map((m) => m.model))];

  const save = async () => {
    setSaving(true);
    setResult(null);
    try {
      const payload = { ...draft };
      for (const [k, v] of Object.entries(keys)) if (v.trim()) payload[k] = v.trim();
      const r = await api.putConfig(payload);
      if (r.ok) {
        if (r.config) {
          setCfg(r.config);
          setDraft(Object.fromEntries(EDITABLE.map((f) => [f, r.config![f]])));
        }
        setKeys({});
        setResult({ ok: true, msg: "Saved and reloaded the bridge." });
      } else {
        setResult({ ok: false, msg: r.error ?? "Save failed." });
      }
    } catch (e) {
      setResult({ ok: false, msg: e instanceof Error ? e.message : String(e) });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <h2 className="font-display text-2xl font-bold tracking-tight text-fg">Settings</h2>
        <p className="mt-1.5 max-w-xl text-sm text-muted">
          Configure the providers your bridge runs. Saved to the host .env and hot-reloaded; API keys
          are write-only and never sent back.
        </p>
      </div>

      {!cfg ? (
        <Panel className="px-5 py-10 text-center text-sm text-muted">
          {result?.msg ?? "loading…"}
        </Panel>
      ) : (
        <>
          <Panel className="flex flex-col gap-4 px-6 py-5">
            <SectionTitle>Language model</SectionTitle>
            <div className="grid grid-cols-2 gap-4">
              <Field label="provider">
                <Select value={draft.llm_provider} options={LLM_PROVIDERS} onChange={(v) => set("llm_provider", v)} />
              </Field>
              <Field label="model">
                <input
                  list="llm-models"
                  className={input}
                  value={draft.llm_model}
                  onChange={(e) => set("llm_model", e.target.value)}
                />
                <datalist id="llm-models">
                  {modelsFor(draft.llm_provider).map((m) => (
                    <option key={m} value={m} />
                  ))}
                </datalist>
              </Field>
            </div>
            <SectionTitle>Vision</SectionTitle>
            <div className="grid grid-cols-3 gap-4">
              <Field label="provider">
                <Select value={draft.vision_provider} options={VISION_PROVIDERS} onChange={(v) => set("vision_provider", v)} />
              </Field>
              <Field label="model">
                <input
                  list="vision-models"
                  className={input}
                  value={draft.vision_model}
                  onChange={(e) => set("vision_model", e.target.value)}
                />
                <datalist id="vision-models">
                  {modelsFor(draft.vision_provider).map((m) => (
                    <option key={m} value={m} />
                  ))}
                </datalist>
              </Field>
              <Field label="ocr">
                <Select value={draft.ocr_provider} options={OCR_PROVIDERS} onChange={(v) => set("ocr_provider", v)} />
              </Field>
            </div>
            <SectionTitle>Ingest disambiguation</SectionTitle>
            <p className="-mt-2 text-xs text-faint">
              Which model decides whether an ingested file&apos;s subject needs a clarifying question.
              Leave blank to use the default language model above.
            </p>
            <div className="grid grid-cols-2 gap-4">
              <Field label="provider">
                <Select
                  value={draft.ambiguity_provider}
                  options={["", ...LLM_PROVIDERS]}
                  onChange={(v) => set("ambiguity_provider", v)}
                />
              </Field>
              <Field label="model">
                <input
                  list="amb-models"
                  className={input}
                  value={draft.ambiguity_model}
                  onChange={(e) => set("ambiguity_model", e.target.value)}
                />
                <datalist id="amb-models">
                  {modelsFor(draft.ambiguity_provider).map((m) => (
                    <option key={m} value={m} />
                  ))}
                </datalist>
              </Field>
            </div>
          </Panel>

          <Panel className="flex flex-col gap-4 px-6 py-5">
            <SectionTitle>CLI tools</SectionTitle>
            <div className="grid grid-cols-2 gap-4">
              <Field label="claude cli path">
                <input className={input} value={draft.claude_cli_path} onChange={(e) => set("claude_cli_path", e.target.value)} />
              </Field>
              <Field label="gemini cli path">
                <input className={input} value={draft.gemini_cli_path} onChange={(e) => set("gemini_cli_path", e.target.value)} />
              </Field>
            </div>
            <Field label="ollama base url">
              <input className={input} value={draft.ollama_base_url} onChange={(e) => set("ollama_base_url", e.target.value)} />
            </Field>
          </Panel>

          <Panel className="flex flex-col gap-4 px-6 py-5">
            <SectionTitle>API keys</SectionTitle>
            {(["anthropic", "openai", "openrouter"] as const).map((name) => (
              <Field key={name} label={`${name} ${cfg.keys[name] ? "· set" : "· not set"}`}>
                <input
                  type="password"
                  className={input}
                  placeholder={cfg.keys[name] ? "•••••• (leave blank to keep)" : "paste a key to set"}
                  value={keys[`${name}_api_key`] ?? ""}
                  onChange={(e) => setKeys((k) => ({ ...k, [`${name}_api_key`]: e.target.value }))}
                />
              </Field>
            ))}
          </Panel>

          <div className="flex items-center justify-end gap-3">
            {result && (
              <span className={result.ok ? "text-xs text-accent" : "text-xs text-danger"}>{result.msg}</span>
            )}
            <Button onClick={save} disabled={saving}>
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
              {saving ? "Saving…" : "Save changes"}
            </Button>
          </div>
        </>
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

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-sm font-semibold text-fg">{children}</h3>;
}

function Select({
  value,
  options,
  onChange,
}: {
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`${input} appearance-none`}
    >
      {!options.includes(value) && <option value={value}>{value}</option>}
      {options.map((o) => (
        <option key={o} value={o} className="bg-panel">
          {o || "(default)"}
        </option>
      ))}
    </select>
  );
}
