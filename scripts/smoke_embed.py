"""Manual smoke test for the bge-m3 embedder. Run from anywhere:
    uv run python scripts/smoke_embed.py

Uses an `if __name__ == "__main__"` guard so FlagEmbedding's worker spawning is safe on
Windows (running the encode via `python -c` deadlocks under the 'spawn' start method).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make repo root importable

from core.config import Settings  # noqa: E402
from providers.factory import build_embeddings  # noqa: E402


async def main() -> None:
    emb = build_embeddings(Settings())
    vecs = await emb.embed(["hello world", "adaptive multimodal rag"])
    print(f"device={emb.device} n={len(vecs)} dim={len(vecs[0])} sample={[round(x, 4) for x in vecs[0][:4]]}")


if __name__ == "__main__":
    asyncio.run(main())
