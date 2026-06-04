"""Application configuration, loaded from environment / .env (see .env.example)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings. Env vars (and a local .env) populate these; env wins over .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Providers. llm_provider in {ollama, anthropic, openai, openrouter, claude-cli, gemini-cli}
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openrouter_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    # CLI backends use the tool's own auth (no key); override the path if not on PATH.
    claude_cli_path: str = "claude"
    gemini_cli_path: str = "gemini"
    llm_provider: str = "ollama"
    llm_model: str = "qwen3:8b-q8_0"
    # vision_provider in {claude-cli, gemini-cli, ollama}. Ollama needs a vision model pulled
    # (e.g. qwen2.5vl); the CLI backends ride their own login. Override model to match the provider.
    vision_provider: str = "claude-cli"
    vision_model: str = "sonnet"
    # Image OCR analyzer (Phase 4B): a dedicated local engine transcribes image text verbatim and
    # fuses it with the vision caption. "easyocr" (GPU, free, exact) or "" / "none" to disable.
    ocr_provider: str = "easyocr"
    embedding_provider: str = "local"
    embedding_model: str = "BAAI/bge-m3"
    # Custom provider adapters: comma-separated import paths; each module calls register_vision /
    # register_llm (providers/registry.py) so a third party plugs in their own backend via config.
    provider_plugins: str = ""

    # Infra
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "adarag_chunks"
    database_url: str = "postgresql+asyncpg://adarag:adarag@localhost:5433/adarag"

    # Retrieval / chunking
    top_k: int = 5
    rerank_candidates: int = 20
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    chunk_size: int = 512
    chunk_overlap: int = 64

    # Enrichment (Phase 2): LLM context prepended per chunk before embedding + carried into rerank.
    # On by default — the A/B (evaluation/BASELINE.md) shows a large end-to-end lift on realistic
    # (topic-named) queries: recall@3 +0.22, MRR +0.20 post-rerank. Costs one LLM call per chunk.
    enrich_context: bool = True
    # Metadata enrichment (Phase 2): entities/dates -> payload filters, keyphrases -> sparse boost.
    # Off by default — its A/B is a retrieval wash (redundant with context); kept for the future
    # query-layer metadata filters (entities/dates land in the payload). See evaluation/BASELINE.md.
    enrich_metadata: bool = False

    # Adaptive chunking (Phase 3): profile each doc -> code-AST / paper-section / notes; else naive.
    adaptive_chunking: bool = True

    # Query layer (Phase 4): LLM rewrites/expands the query before retrieval; rerank on original.
    rewrite_query: bool = False
    # HyDE (Phase 4): retrieve with a generated hypothetical answer instead of the bare query.
    hyde: bool = False
    # Metadata filter (Phase 4): extract query entities, filter retrieval to chunks sharing them.
    metadata_filter: bool = False

    # Cost / tuning
    cost_budget: str = "balanced"


@lru_cache
def get_settings() -> Settings:
    """Cached singleton so settings are read once per process."""
    return Settings()
