"use client";

import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

// Render an assistant message as markdown: bold, lists, headings, blockquotes, tables, inline code,
// and fenced code blocks - styled to the app's dark theme (no default prose).
const components: Components = {
  p: ({ children }) => <p className="text-sm leading-relaxed text-fg">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-fg">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-accent underline decoration-accent/40 underline-offset-2 transition-colors hover:decoration-accent"
    >
      {children}
    </a>
  ),
  ul: ({ children }) => (
    <ul className="ml-4 list-disc space-y-1 text-sm text-fg marker:text-faint">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="ml-4 list-decimal space-y-1 text-sm text-fg marker:text-faint">{children}</ol>
  ),
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  h1: ({ children }) => <h1 className="font-display text-lg font-bold text-fg">{children}</h1>,
  h2: ({ children }) => <h2 className="font-display text-base font-bold text-fg">{children}</h2>,
  h3: ({ children }) => <h3 className="text-sm font-semibold text-fg">{children}</h3>,
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-accent/50 pl-3 italic text-muted">{children}</blockquote>
  ),
  code: ({ children }) => (
    <code className="rounded bg-panel-2 px-1 py-0.5 font-mono text-[12px] text-accent">{children}</code>
  ),
  pre: ({ children }) => (
    <pre className="overflow-x-auto rounded-lg border border-line bg-bg p-3 font-mono text-[12px] leading-relaxed text-fg">
      {children}
    </pre>
  ),
  hr: () => <hr className="my-1 border-line" />,
  table: ({ children }) => (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-xs">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-line px-2 py-1 text-left font-medium text-muted">{children}</th>
  ),
  td: ({ children }) => <td className="border border-line px-2 py-1 text-fg">{children}</td>,
};

export function MarkdownMessage({ text }: { text: string }) {
  return (
    <div className="md-body flex flex-col gap-2">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {text}
      </ReactMarkdown>
    </div>
  );
}
