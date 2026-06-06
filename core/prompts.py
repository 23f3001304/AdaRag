"""Answer prompt templates for the chat scope switch.

A chat picks one of three scopes per turn:
- strict: only answer from the retrieved context, otherwise say you don't know.
- medium: prefer the context, but allow general knowledge when context is silent (marked clearly).
- lazy: open - context is reference, general knowledge and tools (when agent mode is on) are fine.
"""

from __future__ import annotations

_STRICT = """Answer the question using only the context below. Cite sources inline as [n].
If the context does not contain the answer, say you don't know.

Context:
{context}

Question: {query}

Answer:"""

_MEDIUM = """Answer the question. Prefer the context below and cite it inline as [n] when you use
it. If the context does not contain the answer, you may use your own knowledge - clearly say
"(general knowledge)" for any claim not grounded in the context.

Context:
{context}

Question: {query}

Answer:"""

_LAZY = """Answer the question helpfully and naturally. The context below is reference material -
cite it inline as [n] when you use it. You are free to use your own knowledge and any tools you
have access to. Mark non-context claims with "(general knowledge)" when it matters.

Context:
{context}

Question: {query}

Answer:"""

_ANSWER_PROMPTS = {"strict": _STRICT, "medium": _MEDIUM, "lazy": _LAZY}


def answer_prompt(scope: str) -> str:
    """The prompt template for one of the three scopes, falling back to strict on bad input."""
    return _ANSWER_PROMPTS.get(scope, _STRICT)
