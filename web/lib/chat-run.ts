import type { Turn } from "@/components/chat-messages";
import {
  type ModeOption,
  type SkillOverride,
  type StreamHandlers,
  chatStream,
  citationsToSources,
  resumeStream,
} from "@/lib/api";

// Reconnect to every chat whose last assistant turn is still pending - the server kept generating
// while the page reloaded. Resumed jobs are tracked so we never start two streams for the same id.
export function resumePending<C extends { id: string; turns: Turn[] }>(
  saved: C[],
  resumed: Set<string>,
  patch: (chatId: string, fn: (t: Turn) => Turn) => void,
): void {
  for (const c of saved) {
    const last = c.turns.at(-1);
    if (!last?.pending || !last.jobId || resumed.has(last.jobId)) continue;
    resumed.add(last.jobId);
    const ctrl = new AbortController();
    const jobId = last.jobId;
    const chatId = c.id;
    driveChat({
      messageId: jobId,
      fresh: null,
      signal: ctrl.signal,
      ensure: () => {}, // the assistant turn already exists from the saved chat
      update: (fn) => patch(chatId, fn),
      onSettled: () => {},
    });
  }
}

export interface DriveOpts {
  messageId: string;
  // a fresh turn's request, or null to resume an existing job by messageId after a reload
  fresh: {
    session_id: string;
    message: string;
    bucket: string;
    mode?: ModeOption;
    skill?: SkillOverride;
  } | null;
  signal: AbortSignal;
  ensure: (query: string | undefined) => void; // create the pending assistant turn (fresh only)
  update: (fn: (t: Turn) => Turn) => void;
  onSettled: () => void;
}

// Run a chat answer (fresh or resumed) and fold its SSE events into the turn. The server keeps
// generating if `signal` aborts; a resume replays the buffered answer, then streams the rest.
export async function driveChat(opts: DriveOpts): Promise<void> {
  let started = opts.fresh === null; // on resume the turn already exists
  let query: string | undefined;
  const grow = (fn: (t: Turn) => Turn) => {
    if (!started) {
      opts.ensure(query);
      started = true;
    }
    opts.update(fn);
  };
  const handlers: StreamHandlers = {
    query: (q) => {
      query = q;
      if (started) opts.update((t) => ({ ...t, query: q }));
    },
    token: (tok) => grow((t) => ({ ...t, text: t.text + tok })),
    thinking: (th) => grow((t) => ({ ...t, thinking: (t.thinking ?? "") + th })),
    done: (cits) => grow((t) => ({ ...t, sources: citationsToSources(cits), pending: false })),
    error: (m) =>
      grow((t) => ({ ...t, text: `${t.text}\n\n_error: ${m}_`, pending: false, errored: true })),
    gone: () =>
      grow((t) => ({
        ...t,
        text: t.text || "_(answer was interrupted - ask again)_",
        pending: false,
        errored: true,
      })),
  };
  try {
    if (opts.fresh) await chatStream({ ...opts.fresh, message_id: opts.messageId }, opts.signal, handlers);
    else await resumeStream(opts.messageId, opts.signal, handlers);
  } catch (e) {
    const aborted = e instanceof DOMException && e.name === "AbortError";
    grow((t) => ({
      ...t,
      text: aborted ? `${t.text} _(stopped)_` : t.text || "request failed - is the CLI bridge running?",
      pending: false,
      errored: true,
    }));
  } finally {
    opts.onSettled();
  }
}
