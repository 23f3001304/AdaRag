"""Application configuration, loaded from environment / .env (see .env.example)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings. Env vars (and a local .env) populate these; env wins over .env."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

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
    vision_provider: str = "anthropic"
    vision_model: str = "claude-sonnet-4-6"
    embedding_provider: str = "local"
    embedding_model: str = "BAAI/bge-m3"

    # Infra
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "adarag_chunks"
    database_url: str = "postgresql+asyncpg://adarag:adarag@localhost:5433/adarag"

    # Retrieval / chunking
    top_k: int = 5
    chunk_size: int = 512
    chunk_overlap: int = 64

    # Cost / tuning
    cost_budget: str = "balanced"


@lru_cache
def get_settings() -> Settings:
    """Cached singleton so settings are read once per process."""
    return Settings()
