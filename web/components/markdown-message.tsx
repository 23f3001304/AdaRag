"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import remarkGfm from "remark-gfm";

function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <div className="overflow-hidden rounded-lg border border-line">
      <div className="flex items-center justify-between border-b border-line bg-panel-2 px-3 py-1.5">
        <span className="font-mono text-[10px] uppercase tracking-wider text-faint">
          {language || "code"}
        </span>
        <button
          onClick={copy}
          className="flex items-center gap-1 font-mono text-[10px] text-faint transition-colors hover:text-accent"
        >
          {copied ? <Check size={11} /> : <Copy size={11} />} {copied ? "copied" : "copy"}
        </button>
      </div>
      <SyntaxHighlighter
        language={language || "text"}
        style={oneDark}
        customStyle={{ margin: 0, background: "var(--color-bg)", fontSize: "12px", padding: "12px" }}
        codeTagProps={{ style: { fontFamily: "var(--font-jetbrains), monospace" } }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}

// Render an assistant message as markdown: bold, lists, headings, blockquotes, tables, inline code,
// and fenced code blocks with a language label, copy button, and syntax highlighting.
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
  pre: ({ children }) => <>{children}</>,
  code: ({ className, children }) => {
    const match = /language-(\w+)/.exec(className || "");
    const text = String(children).replace(/\n$/, "");
    if (match || text.includes("\n")) return <CodeBlock language={match?.[1] ?? ""} code={text} />;
    return (
      <code className="rounded bg-panel-2 px-1 py-0.5 font-mono text-[12px] text-accent">{children}</code>
    );
  },
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
