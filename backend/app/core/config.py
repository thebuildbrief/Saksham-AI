"""Validated settings; sensitive values use SecretStr and are never represented as plaintext."""
import secrets
from typing import List
from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def secret_value(value) -> str:
    return value.get_secret_value() if isinstance(value, SecretStr) else str(value or "")


class Settings(BaseSettings):
    APP_NAME: str = "SAKSHAM AI"
    APP_ENV: str = "development"
    DEBUG: bool = False
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    APP_SECRET_KEY: SecretStr = SecretStr("")
    JWT_SECRET_KEY: SecretStr = SecretStr("")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    FRONTEND_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    DATABASE_URL: SecretStr = SecretStr("sqlite:///./saksham.db")
    DATABASE_POOL_SIZE: int = 1
    REDIS_URL: SecretStr = SecretStr("")
    AI_PROVIDER: str = "mock"
    AI_MODEL: str = ""
    AI_REQUEST_TIMEOUT_SECONDS: float = 20.0
    OPENAI_API_KEY: SecretStr = SecretStr("")
    GEMINI_API_KEY: SecretStr = SecretStr("")
    GROQ_API_KEY: SecretStr = SecretStr("")
    ANTHROPIC_API_KEY: SecretStr = SecretStr("")
    VOICE_PROVIDER: str = "browser"
    ELEVENLABS_API_KEY: SecretStr = SecretStr("")
    ELEVENLABS_VOICE_ID: str = ""
    JUDGE0_API_URL: str = ""
    JUDGE0_API_KEY: SecretStr = SecretStr("")
    CODE_CPU_TIME_LIMIT: float = 2.0
    CODE_WALL_TIME_LIMIT: float = 5.0
    CODE_MEMORY_LIMIT_KB: int = 256000
    CODE_PROVIDER_TIMEOUT_SECONDS: float = 12.0
    CODE_REQUEST_TIMEOUT_SECONDS: float = 30.0
    CODE_MAX_CONCURRENT: int = 4
    CODE_MAX_REQUESTS_PER_MINUTE: int = 10
    CODE_MAX_TEST_CASES: int = 20
    STORAGE_PROVIDER: str = "local"
    STORAGE_LOCAL_DIR: str = "./storage/uploads"
    STORAGE_S3_BUCKET: str = ""
    STORAGE_S3_REGION: str = ""
    STORAGE_S3_ENDPOINT_URL: str = ""
    STORAGE_S3_ACCESS_KEY_ID: SecretStr = SecretStr("")
    STORAGE_S3_SECRET_ACCESS_KEY: SecretStr = SecretStr("")
    MAX_RESUME_SIZE_BYTES: int = 3 * 1024 * 1024
    SUBSCRIPTION_PROVIDER: str = "none"
    STRIPE_SECRET_KEY: SecretStr = SecretStr("")
    STRIPE_PRICE_ID: str = ""
    STRIPE_WEBHOOK_SECRET: SecretStr = SecretStr("")
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_deployment(self):
        production = self.APP_ENV.strip().lower() in {"production", "prod"}
        for field in ("APP_SECRET_KEY", "JWT_SECRET_KEY"):
            value = secret_value(getattr(self, field))
            if not value:
                if production:
                    raise ValueError(f"{field} is required in production")
                value = secrets.token_urlsafe(32)
                setattr(self, field, SecretStr(value))
            if len(value) < 32:
                raise ValueError("Application signing secrets must be at least 32 characters")
        if self.JWT_ALGORITHM != "HS256":
            raise ValueError("Only HS256 is supported for JWT signing")
        if not 1024 <= self.MAX_RESUME_SIZE_BYTES <= 4 * 1024 * 1024:
            raise ValueError("MAX_RESUME_SIZE_BYTES must be between 1 KiB and 4 MiB")
        if production:
            if self.DEBUG:
                raise ValueError("DEBUG must be false in production")
            if not secret_value(self.DATABASE_URL).lower().startswith(("postgresql://", "postgres://", "postgresql+psycopg://")):
                raise ValueError("Production DATABASE_URL must use PostgreSQL")
            if self.AI_PROVIDER.lower() not in {"openai", "gemini", "groq", "anthropic"}:
                raise ValueError("Production AI_PROVIDER must be a supported external provider")
            ai_key_field = {"openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}[self.AI_PROVIDER.lower()]
            if not secret_value(getattr(self, ai_key_field)):
                raise ValueError("A credential for the configured AI_PROVIDER is required in production")
            if not self.JUDGE0_API_URL.startswith("https://") or not secret_value(self.JUDGE0_API_KEY):
                raise ValueError("Production requires an HTTPS Judge0 URL and API key")
            if not secret_value(self.REDIS_URL).startswith(("redis://", "rediss://")):
                raise ValueError("Production requires Redis for distributed execution limits")
            if self.STORAGE_PROVIDER.lower() != "s3" or not self.STORAGE_S3_BUCKET or not secret_value(self.STORAGE_S3_ACCESS_KEY_ID) or not secret_value(self.STORAGE_S3_SECRET_ACCESS_KEY):
                raise ValueError("Production requires configured private S3-compatible object storage")
            if not self.cors_origins or any(not origin.startswith("https://") for origin in self.cors_origins):
                raise ValueError("Production FRONTEND_ORIGINS must contain HTTPS origins")
            if self.VOICE_PROVIDER.lower() == "elevenlabs" and (not secret_value(self.ELEVENLABS_API_KEY) or not self.ELEVENLABS_VOICE_ID):
                raise ValueError("ElevenLabs voice configuration is incomplete")
            if self.SUBSCRIPTION_PROVIDER.lower() == "stripe" and (not secret_value(self.STRIPE_SECRET_KEY) or not self.STRIPE_PRICE_ID or not secret_value(self.STRIPE_WEBHOOK_SECRET)):
                raise ValueError("Stripe subscription configuration is incomplete")
        return self

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip().rstrip("/") for origin in self.FRONTEND_ORIGINS.split(",") if origin.strip()]


settings = Settings()
