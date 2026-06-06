"use client";

import { useEffect, useRef, useState } from "react";

import { AgentToggle } from "@/components/agent-toggle";
import { useBucket } from "@/components/bucket-context";
import { ChatComposer } from "@/components/chat-composer";
import { ChatList } from "@/components/chat-list";
import { ChatMessages, type Turn } from "@/components/chat-messages";
import { Chip } from "@/components/chip";
import { useIngest } from "@/components/ingest-context";
import { ModePicker } from "@/components/mode-picker";
import { useNotify } from "@/components/notification-context";
import { type Resource, ResourceModal } from "@/components/resource-modal";
import { type ModeOption, api } from "@/lib/api";
import { driveChat, resumePending } from "@/lib/chat-run";
import { isSkillRequest } from "@/lib/skill-intent";
import { loadSkills, saveSkills, type Skill } from "@/lib/skills";

interface Chat {
  id: string;
  title: string;
  session: string;
  turns: Turn[];
  mode?: ModeOption;
  agent?: boolean;
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
  const { notify } = useNotify();
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
  const currentJob = useRef<string | null>(null);
  const resumedJobs = useRef<Set<string>>(new Set());
  const stop = () => {
    abortRef.current?.abort();
    if (currentJob.current) api.stopChat(currentJob.current).catch(() => {});
  };

  useEffect(() => {
    api.listModes().then((r) => setModes(r.modes)).catch(() => {});
    const sync = () => setSkills(loadSkills());
    sync();
    window.addEventListener("focus", sync);
    return () => window.removeEventListener("focus", sync);
  }, []);

  const patchTurn = (chatId: string, fn: (t: Turn) => Turn) =>
    setChats((cs) => {
      const next = cs.map((x) => {
        if (x.id !== chatId || !x.turns.length) return x;
        const turns = [...x.turns];
        turns[turns.length - 1] = fn(turns[turns.length - 1]);
        return { ...x, turns };
      });
      localStorage.setItem(KEY, JSON.stringify(next));
      return next;
    });

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
    // Reconnect to any answer still generating before the reload (server kept producing tokens).
    resumePending(saved, resumedJobs.current, (chatId, fn) => patchTurn(chatId, fn));
  }, []);

  const active = chats.find((c) => c.id === activeId);
  const persist = (next: Chat[]) => {
    setChats(next);
    localStorage.setItem(KEY, JSON.stringify(next));
  };
  const setChatMode = (mode: ModeOption | undefined) =>
    persist(chats.map((c) => (c.id === activeId ? { ...c, mode } : c)));
  const toggleAgent = () =>
    persist(chats.map((c) => (c.id === activeId ? { ...c, agent: !c.agent } : c)));
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
      notify({ kind: "success", title: "Skill created", body: d.name });
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

  const continueTurn = (turnIndex: number) => {
    if (!active || busy) return;
    // Find the user message that produced this errored answer, drop the errored turn, and re-send.
    let user: Turn | undefined;
    for (let i = turnIndex - 1; i >= 0; i--) {
      if (active.turns[i].role === "user") {
        user = active.turns[i];
        break;
      }
    }
    if (!user) return;
    const trimmed = active.turns.slice(0, turnIndex);
    persist(chats.map((c) => (c.id === active.id ? { ...c, turns: trimmed } : c)));
    void send(user.text, null);
  };

  const send = async (text: string, file: File | null) => {
    if ((!text && !file) || busy || !active) return;
    if (creating && text) return createSkill(text);
    // Skill intent: a client heuristic gates the LLM call so questions never pay for the round-trip.
    if (text && !file && (await isSkillRequest(text))) return createSkill(text);
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
    const messageId = crypto.randomUUID();
    currentJob.current = messageId;
    await driveChat({
      messageId,
      fresh: { session_id: active.session, message: text, bucket, mode: active.mode, skill, agent: !!active.agent },
      signal: ctrl.signal,
      ensure: (query) =>
        pushAssistant(base, { role: "assistant", text: "", query, pending: true, jobId: messageId }),
      update: (fn) => patchTurn(activeId, fn),
      onSettled: () => {
        if (currentJob.current === messageId) currentJob.current = null;
        setBusy(false);
      },
    });
  };

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-5">
      <ChatList chats={chats} activeId={activeId} onSelect={select} onAdd={addChat} onDelete={delChat} />

      <div className="flex min-w-0 flex-1 flex-col rounded-xl border border-line bg-panel/30">
        <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-2">
          <div className="flex min-w-0 items-center gap-2">
            <ModePicker modes={modes} value={active?.mode} onChange={setChatMode} />
            <AgentToggle on={!!active?.agent} onToggle={toggleAgent} />
            {activeSkill && <Chip onClear={() => setActiveSkill(null)}>{activeSkill.name}</Chip>}
            {creating && <Chip onClear={() => setCreating(false)}>creating skill…</Chip>}
          </div>
          <span className="shrink-0 font-mono text-[10px] text-faint">
            bucket: <span className="text-muted">{bucket}</span>
          </span>
        </div>
        <div className="flex-1 space-y-5 overflow-y-auto p-6">
          <ChatMessages turns={active?.turns ?? []} busy={busy} bucket={bucket} onPreview={setPreview} onContinue={continueTurn} />
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

