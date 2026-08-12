from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ForgeOps API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://forgeops:forgeops-local-only@localhost:5432/forgeops"
    secret_key: str = "development-key-change-before-deployment-2026"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    frontend_url: str = "http://localhost:3000"
    cookie_secure: bool = False
    upload_directory: str = "uploads"
    max_upload_bytes: int = 15 * 1024 * 1024
    ai_provider: str = "local"
    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-5"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    rag_chunk_chars: int = 1400
    rag_chunk_overlap: int = 200
    rag_top_k: int = 5
    rag_max_document_chars: int = 2_000_000
    rag_min_semantic_score: float = Field(default=0.25, ge=0, le=1)
    rag_relative_score_floor: float = Field(default=0.72, ge=0, le=1)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SECRET_KEY debe tener al menos 32 caracteres")
        return value

    @field_validator("ai_provider")
    @classmethod
    def validate_ai_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"local", "openai"}:
            raise ValueError("AI_PROVIDER debe ser local u openai")
        return normalized

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.app_env.lower() == "production":
            if self.secret_key.startswith("development-"):
                raise ValueError("SECRET_KEY debe cambiarse en produccion")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE debe estar activo en produccion")
            if any("localhost" in origin for origin in self.allowed_origins):
                raise ValueError("FRONTEND_URL no puede apuntar a localhost en produccion")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_url.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
