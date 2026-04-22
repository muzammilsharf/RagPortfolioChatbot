from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # CORS
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Rate limiting
    rate_limit_per_minute: int = 10

    # Groq
    groq_api_key: str | None = None
    groq_model: str = "llama3-8b-8192"
    groq_max_tokens: int = 500

    # LLM provider (groq | gemini)
    llm_provider: str = "groq"
    allow_provider_fallback: bool = True
    # Optional: full automatic routing across multiple models/providers.
    # Format: "groq:llama-3.3-70b-versatile,groq:llama3-8b-8192,gemini:gemini-2.5-flash,gemini:gemini-2.0-flash"
    llm_candidates: str = ""
    # Mark a model unhealthy for this long after a 429/503/timeout.
    llm_cooldown_seconds: float = 90.0
    # If we don't see a first token quickly, try next candidate.
    llm_first_token_timeout_seconds: float = 1.2

    # Gemini (Google GenAI)
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_fallback_model: str = "gemini-2.0-flash"
    gemini_retries: int = 2
    gemini_retry_backoff_seconds: float = 0.6
    gemini_max_output_tokens: int = 500

    # Security
    admin_api_key: str | None = None

    # Retrieval
    top_k: int = 8
    min_similarity: float = 0.12  # lower => more conversational; still grounded via prompt
    hybrid_candidate_k: int = 12
    hybrid_vector_weight: float = 0.75
    hybrid_keyword_weight: float = 0.25

    # Memory
    memory_turns: int = 5

    # Data locations
    raw_documents_dir: str = "data/raw_documents"
    chroma_persist_dir: str = "data/vector_store"
    chroma_collection: str = "portfolio"

    # Chunking
    chunk_size_tokens: int = 250
    chunk_overlap_tokens: int = 30

    # Prompt/context size controls (reduces latency + cost)
    max_context_chunks: int = 4
    max_chunk_chars: int = 1200


settings = Settings()
