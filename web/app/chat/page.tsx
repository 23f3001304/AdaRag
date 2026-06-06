"use client";

import { Boxes, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useBucket } from "@/components/bucket-context";
import { ChatComposer } from "@/components/chat-composer";
import { ChatList } from "@/components/chat-list";
import { ChatMessages, type Source, type Turn } from "@/components/chat-messages";
import { useIngest } from "@/components/ingest-context";
import { ModePicker } from "@/components/mode-picker";
import { type Resource, ResourceModal } from "@/components/resource-modal";
import { type ModeOption, api, chatStream, citationsToSources } from "@/lib/api";
import { loadSkills, saveSkills, type Skill } from "@/lib/skills";

interface Chat {
  id: string;
  title: string;
  session: string;
  turns: Turn[];
  mode?: ModeOption;
}

const KEY = "adarag.chats";
const fresh = (): Chat => ({
  id: crypto.randomUUID(),
  title: "New chat",
  session: crypto.randomUUID(),
  turns: [],
});

export default function ChatPage() {
  const { bucket } = useBucket();
  const { ingest: ingestFile } = useIngest();
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeId, setActiveId] = useState("");
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<Resource | null>(null);
  const [modes, setModes] = useState<ModeOption[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [activeSkill, setActiveSkill] = useState<Skill | null>(null);
  const [creating, setCreating] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const stop = () => abortRef.current?.abort();

  useEffect(() => {
    api.listModes().then((r) => setModes(r.modes)).catch(() => {});
    const sync = () => setSkills(loadSkills());
    sync();
    window.addEventListener("focus", sync);
    return () => window.removeEventListener("focus", sync);
  }, []);

  useEffect(() => {
    let saved: Chat[] = [];
    try {
      saved = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    } catch {
      saved = [];
    }
    if (!saved.length) saved = [fresh()];
    /* eslint-disable react-hooks/set-state-in-effect */
    setChats(saved);
    setActiveId(saved[0].id);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, []);

  const active = chats.find((c) => c.id === activeId);
  const persist = (next: Chat[]) => {
    setChats(next);
    localStorage.setItem(KEY, JSON.stringify(next));
  };
  const setChatMode = (mode: ModeOption | undefined) =>
    persist(chats.map((c) => (c.id === activeId ? { ...c, mode } : c)));
  const select = (id: string) => {
    setActiveId(id);
    setActiveSkill(null);
    setCreating(false);
  };

  const pushUser = (text: string, file?: string) => {
    const next = chats.map((c) =>
      c.id === activeId
        ? {
            ...c,
            title: c.turns.length ? c.title : text.slice(0, 38) || file || "New chat",
            turns: [...c.turns, { role: "user" as const, text, file }],
          }
        : c,
    );
    persist(next);
    return next;
  };
  const pushAssistant = (base: Chat[], turn: Turn) =>
    persist(base.map((c) => (c.id === activeId ? { ...c, turns: [...c.turns, turn] } : c)));
  // Mutate the active chat's last turn (used to grow the streaming answer token by token).
  const updateLast = (fn: (t: Turn) => Turn) =>
    setChats((cs) => {
      const next = cs.map((c) => {
        if (c.id !== activeId || !c.turns.length) return c;
        const turns = [...c.turns];
        turns[turns.length - 1] = fn(turns[turns.length - 1]);
        return { ...c, turns };
      });
      localStorage.setItem(KEY, JSON.stringify(next));
      return next;
    });

  const createSkill = async (description: string) => {
    if (busy) return;
    const base = pushUser(description);
    setCreating(false);
    setBusy(true);
    try {
      const d = await api.draftSkill(description);
      const skill: Skill = {
        id: crypto.randomUUID(),
        name: d.name,
        bucket,
        persona: d.persona,
        topK: d.top_k,
        rerank: 20,
        enrich: true,
        templates: [],
      };
      const next = [...loadSkills(), skill];
      saveSkills(next);
      setSkills(next);
      setActiveSkill(skill);
      const slug = d.name.toLowerCase().replace(/\s+/g, "-");
      pushAssistant(base, {
        role: "assistant",
        text: `Created skill **${d.name}** (top_k ${d.top_k}) and applied it. Reuse it anytime with \`/${slug}\`.\n\n> ${d.persona}`,
      });
    } catch {
      pushAssistant(base, {
        role: "assistant",
        text: "couldn't draft a skill - is the CLI bridge running?",
      });
    } finally {
      setBusy(false);
    }
  };

  const onPick = (target: Skill | "creator", description?: string) => {
    if (target !== "creator") {
      setActiveSkill(target);
      setCreating(false);
      return;
    }
    setActiveSkill(null);
    if (description?.trim()) {
      void createSkill(description.trim());
    } else {
      setCreating(true);
      if (active) {
        pushAssistant(chats, {
          role: "assistant",
          text: "Describe the assistant you want and I'll build a skill - for example: *a terse security analyst that always cites sources and flags risks*.",
        });
      }
    }
  };

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [active?.turns.length, busy]);

  const addChat = () => {
    const c = fresh();
    persist([c, ...chats]);
    select(c.id);
  };
  const delChat = (id: string) => {
    const next = chats.filter((c) => c.id !== id);
    const safe = next.length ? next : [fresh()];
    persist(safe);
    if (id === activeId) select(safe[0].id);
  };

  const send = async (text: string, file: File | null) => {
    if ((!text && !file) || busy || !active) return;
    if (creating && text) return createSkill(text);
    const base = pushUser(text, file?.name);
    setBusy(true);
    if (file) {
      // Attached file: route ingest-vs-ask. Ingest fires through the Ingest tab in the background
      // so it never hangs the chat; any "who/what is this?" question bubbles up there.
      try {
        const intent = text ? (await api.route(text)).intent : "ingest";
        if (intent === "ingest") {
          ingestFile(file, bucket, text); // the message doubles as optional context for the file
          pushAssistant(base, {
            role: "assistant",
            text: `Ingesting **${file.name}** into the ${bucket} bucket - track it on the Ingest tab. I'll raise a question there if I can't tell who or what it's about.`,
          });
          setBusy(false);
          return;
        }
      } catch {
        pushAssistant(base, { role: "assistant", text: "couldn't route the file - is the CLI bridge running?" });
        setBusy(false);
        return;
      }
    }
    const skill = activeSkill ? { persona: activeSkill.persona, top_k: activeSkill.topK } : undefined;
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    let started = false;
    let q: string | undefined; // hold the search query until the bubble is created
    const grow = (fn: (t: Turn) => Turn) => {
      if (!started) {
        pushAssistant(base, { role: "assistant", text: "", query: q });
        started = true;
      }
      updateLast(fn);
    };
    try {
      await chatStream(
        { session_id: active.session, message: text, bucket, mode: active.mode, skill },
        ctrl.signal,
        {
          // Don't open the bubble on the query event - keep the dots until real content arrives.
          query: (query) => {
            q = query;
            if (started) updateLast((t) => ({ ...t, query }));
          },
          token: (tok) => grow((t) => ({ ...t, text: t.text + tok })),
          thinking: (th) => grow((t) => ({ ...t, thinking: (t.thinking ?? "") + th })),
          done: (cits) => grow((t) => ({ ...t, sources: citationsToSources(cits) })),
          error: (m) => grow((t) => ({ ...t, text: `${t.text}\n\n_error: ${m}_` })),
        },
      );
    } catch (e) {
      const aborted = e instanceof DOMException && e.name === "AbortError";
      grow((t) => ({
        ...t,
        text: aborted ? `${t.text} _(stopped)_` : t.text || "request failed - is the CLI bridge running?",
      }));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-5">
      <ChatList chats={chats} activeId={activeId} onSelect={select} onAdd={addChat} onDelete={delChat} />

      <div className="flex min-w-0 flex-1 flex-col rounded-xl border border-line bg-panel/30">
        <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-2">
          <div className="flex min-w-0 items-center gap-2">
            <ModePicker modes={modes} value={active?.mode} onChange={setChatMode} />
            {activeSkill && <Chip onClear={() => setActiveSkill(null)}>{activeSkill.name}</Chip>}
            {creating && <Chip onClear={() => setCreating(false)}>creating skill…</Chip>}
          </div>
          <span className="shrink-0 font-mono text-[10px] text-faint">
            bucket: <span className="text-muted">{bucket}</span>
          </span>
        </div>
        <div className="flex-1 space-y-5 overflow-y-auto p-6">
          <ChatMessages turns={active?.turns ?? []} busy={busy} bucket={bucket} onPreview={setPreview} />
          <div ref={endRef} />
        </div>
        <ChatComposer
          onSend={send}
          onPick={onPick}
          onStop={stop}
          skills={skills}
          busy={busy}
          placeholder={creating ? "describe the skill you want…" : undefined}
        />
      </div>

      <ResourceModal resource={preview} onClose={() => setPreview(null)} />
    </div>
  );
}

function Chip({ children, onClear }: { children: React.ReactNode; onClear: () => void }) {
  return (
    <span className="flex items-center gap-1 rounded border border-accent/40 bg-accent/10 px-2 py-1 text-xs text-accent">
      <Boxes size={11} />
      <span className="max-w-32 truncate">{children}</span>
      <button onClick={onClear} className="transition-colors hover:text-fg">
        <X size={11} />
      </button>
    </span>
  );
}
