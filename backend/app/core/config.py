"""
Application Configuration Settings for SAKSHAM AI.
Loads settings from environment variables or .env file with safe defaults.
"""
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator


class Settings(BaseSettings):
    APP_NAME: str = "SAKSHAM AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Security & Tokens
    APP_SECRET_KEY: str = "saksham_super_secret_master_key_2026_change_in_production"
    JWT_SECRET_KEY: str = "saksham_jwt_hmac_secret_key_32_characters_minimum"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours for dev ease
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    FRONTEND_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    # Database
    DATABASE_URL: str = "sqlite:///./saksham.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI & Providers
    AI_PROVIDER: str = "mock"  # 'gemini' | 'openai' | 'groq' | 'anthropic' | 'mock'
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Voice Providers
    VOICE_PROVIDER: str = "browser"  # 'browser' | 'elevenlabs' | 'openai'
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = ""

    # Judge0 Code Sandbox
    JUDGE0_API_URL: str = ""
    JUDGE0_API_KEY: str = ""
    CODE_CPU_TIME_LIMIT: float = 2.0
    CODE_WALL_TIME_LIMIT: float = 5.0
    CODE_MEMORY_LIMIT_KB: int = 256000
    CODE_PROVIDER_TIMEOUT_SECONDS: float = 12.0
    CODE_REQUEST_TIMEOUT_SECONDS: float = 30.0
    CODE_MAX_CONCURRENT: int = 4
    CODE_MAX_TEST_CASES: int = 20

    # Storage
    STORAGE_PROVIDER: str = "local"
    STORAGE_LOCAL_DIR: str = "./storage/uploads"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.FRONTEND_ORIGINS.split(",") if origin.strip()]


settings = Settings()
