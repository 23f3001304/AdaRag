"""Local bge-m3 embeddings (dense) via FlagEmbedding. Implements EmbeddingProvider."""

from __future__ import annotations

import asyncio
from typing import Any


class BGEM3Embeddings:
    """bge-m3 dense embeddings. The model loads lazily on first use (weights are ~2 GB).

    Picks CUDA automatically when a GPU is visible (fp16), otherwise CPU (fp32).
    """

    dim = 1024

    def __init__(self, model_name: str = "BAAI/bge-m3") -> None:
        self._model_name = model_name
        self._model: Any | None = None
        self.device = "cpu"  # resolved on first load

    def _load(self) -> Any:
        if self._model is None:
            import torch  # heavy import, deferred
            from FlagEmbedding import BGEM3FlagModel

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model = BGEM3FlagModel(
                self._model_name, use_fp16=(self.device == "cuda"), devices=self.device
            )
        return self._model

    def _encode(self, texts: list[str]) -> list[list[float]]:
        out = self._load().encode(texts, return_dense=True, return_sparse=False)
        return [vec.tolist() for vec in out["dense_vecs"]]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts into 1024-dim dense vectors (the blocking model call runs in a thread)."""
        if not texts:
            return []
        return await asyncio.to_thread(self._encode, texts)

    def _encode_hybrid(self, texts: list[str]) -> tuple[list[list[float]], list[dict[int, float]]]:
        out = self._load().encode(texts, return_dense=True, return_sparse=True)
        dense = [vec.tolist() for vec in out["dense_vecs"]]
        sparse = [{int(tok): float(w) for tok, w in lw.items()} for lw in out["lexical_weights"]]
        return dense, sparse

    async def embed_hybrid(
        self, texts: list[str]
    ) -> tuple[list[list[float]], list[dict[int, float]]]:
        """Embed texts into dense + sparse (lexical) vectors in a single bge-m3 pass."""
        if not texts:
            return [], []
        return await asyncio.to_thread(self._encode_hybrid, texts)
