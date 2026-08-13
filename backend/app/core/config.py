from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ForgeOps API"
    app_env: Literal["development", "testing", "staging", "production"] = "development"
    app_version: str = "1.2.2"
    build_commit: str = Field(
        default="local",
        validation_alias=AliasChoices("RAILWAY_GIT_COMMIT_SHA", "BUILD_COMMIT"),
    )
    api_prefix: str = "/api/v1"
    api_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    control_url: str = "http://localhost:3000/control"
    cors_origins: str = ""
    debug: bool = False
    docs_enabled: bool = True
    maintenance_mode: bool = False
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://forgeops:forgeops-local-only@localhost:5432/forgeops"
    migration_database_url: str | None = None
    database_pool_mode: Literal["direct", "pgbouncer"] = "direct"
    database_runtime_role: str | None = "forgeops_runtime"
    database_user_is_restricted: bool = False
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=200)
    database_pool_timeout_seconds: int = Field(default=15, ge=1, le=120)
    database_pool_recycle_seconds: int = Field(default=900, ge=30, le=7200)
    database_connect_timeout_seconds: int = Field(default=10, ge=1, le=60)
    database_statement_timeout_ms: int = Field(default=30000, ge=1000, le=300000)

    redis_url: str = "redis://localhost:6379/0"
    redis_required: bool = False
    redis_socket_timeout_seconds: int = Field(default=3, ge=1, le=30)
    rate_limit_enabled: bool = True
    rate_limit_login: str = "10/60"
    rate_limit_trial_signup: str = "5/3600"
    rate_limit_password_reset: str = "5/3600"
    rate_limit_upload: str = "30/3600"
    job_queue_name: str = "forgeops"
    job_max_attempts: int = Field(default=3, ge=1, le=10)
    job_dispatch_enabled: bool = True

    secret_key: str = "development-key-change-before-deployment-2026"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    operator_access_token_minutes: int = Field(default=10, ge=5, le=30)
    operator_refresh_token_hours: int = Field(default=8, ge=1, le=24)
    operator_lockout_attempts: int = Field(default=5, ge=3, le=10)
    operator_lockout_minutes: int = Field(default=15, ge=1, le=60)
    cookie_secure: bool = False
    cookie_domain: str | None = None
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    trial_days: int = Field(default=30, ge=1, le=90)
    trial_signup_enabled: bool = True
    seed_demo_data: bool = False
    allow_demo_seed: bool = True
    global_feature_flags: str = ""

    storage_backend: Literal["local", "s3"] = "local"
    upload_directory: str = "uploads"
    max_upload_bytes: int = 15 * 1024 * 1024
    storage_signed_url_seconds: int = Field(default=300, ge=30, le=3600)
    s3_endpoint: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket: str | None = None
    s3_region: str = "eu-west-1"
    s3_force_path_style: bool = True

    email_backend: Literal["development", "smtp"] = "development"
    email_from_address: str = "no-reply@forgeops.local"
    email_from_name: str = "ForgeOps"
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True

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

    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = Field(default=0.05, ge=0, le=1)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SECRET_KEY debe tener al menos 32 caracteres")
        return value

    @field_validator("database_url", "migration_database_url", mode="before")
    @classmethod
    def normalize_postgresql_driver(cls, value):
        if isinstance(value, str) and value.startswith(("postgres://", "postgresql://")):
            return "postgresql+psycopg://" + value.split("://", 1)[1]
        return value

    @field_validator("ai_provider")
    @classmethod
    def validate_ai_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"local", "openai"}:
            raise ValueError("AI_PROVIDER debe ser local u openai")
        return normalized

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL no es valido")
        return normalized

    @model_validator(mode="after")
    def validate_security(self):
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE debe estar activo con COOKIE_SAMESITE=none")
        if self.seed_demo_data and not self.allow_demo_seed:
            raise ValueError("SEED_DEMO_DATA requiere ALLOW_DEMO_SEED=true")
        if self.app_env != "production":
            return self

        errors: list[str] = []
        origins = self.allowed_origins
        urls = [self.api_url, self.frontend_url, self.control_url, *origins]
        if self.debug:
            errors.append("DEBUG debe estar desactivado")
        if self.secret_key.startswith("development-"):
            errors.append("SECRET_KEY debe cambiarse")
        if not self.cookie_secure:
            errors.append("COOKIE_SECURE debe estar activo")
        if "*" in origins:
            errors.append("CORS no admite wildcard")
        if any(self._is_local_url(value) for value in urls):
            errors.append("las URLs publicas no pueden apuntar a localhost")
        if not self.database_url.startswith("postgresql+"):
            errors.append("DATABASE_URL debe utilizar PostgreSQL")
        if self.migration_database_url and not self.migration_database_url.startswith(
            "postgresql+"
        ):
            errors.append("MIGRATION_DATABASE_URL debe utilizar PostgreSQL")
        if self.database_pool_mode == "pgbouncer" and self.database_runtime_role:
            errors.append(
                "PgBouncer requiere credenciales de rol restringido y DATABASE_RUNTIME_ROLE vacio"
            )
        if not self.database_runtime_role and not self.database_user_is_restricted:
            errors.append("el usuario de base de datos debe declararse restringido")
        if self.storage_backend != "s3":
            errors.append("STORAGE_BACKEND debe ser s3")
        if not all([self.s3_endpoint, self.s3_access_key, self.s3_secret_key, self.s3_bucket]):
            errors.append("faltan credenciales o bucket S3")
        if not self.redis_url.startswith(("redis://", "rediss://")):
            errors.append("REDIS_URL no es valida")
        if self._is_local_url(self.redis_url):
            errors.append("REDIS_URL no puede apuntar a localhost")
        if self.seed_demo_data or self.allow_demo_seed:
            errors.append("la carga demo debe estar desactivada")
        if self.email_backend != "smtp" or not self.smtp_host:
            errors.append("EMAIL_BACKEND y SMTP_HOST deben estar configurados")
        if not self.job_dispatch_enabled:
            errors.append("JOB_DISPATCH_ENABLED debe estar activo")
        if errors:
            raise ValueError("Configuracion de produccion insegura: " + "; ".join(errors))
        return self

    @property
    def allowed_origins(self) -> list[str]:
        source = self.cors_origins or self.frontend_url
        origins = (origin.strip().rstrip("/") for origin in source.split(","))
        return list(dict.fromkeys(origin for origin in origins if origin))

    @property
    def feature_flags(self) -> frozenset[str]:
        flags = (flag.strip().upper() for flag in self.global_feature_flags.split(","))
        return frozenset(flag for flag in flags if flag)

    @staticmethod
    def _is_local_url(value: str) -> bool:
        hostname = urlparse(value).hostname
        return hostname in {"localhost", "127.0.0.1", "::1"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
