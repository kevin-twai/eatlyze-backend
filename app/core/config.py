# app/core/config.py
from __future__ import annotations

from functools import lru_cache
from typing import Any, List, Optional

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # === App Info ===
    APP_NAME: str = "Eatlyze API"
    API_V1_PREFIX: str = "/api/v1"
    ENV: str = "dev"
    DEBUG: bool = True

    # === CORS ===
    # 支援 .env 內用 JSON 字串或逗號分隔字串
    CORS_ORIGINS: List[AnyHttpUrl] | List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json
                return json.loads(v)
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    # === Database ===
    # 預設本機 Docker 的連線字串；CI 或雲端可用環境變數覆蓋
    DATABASE_URL: str = "postgresql+asyncpg://eatlyze:eatlyze@localhost:5432/eatlyze"
    DB_ECHO: bool = False

    # === Auth / JWT ===
    SECRET_KEY: str = "change_this_to_a_long_random_string"
    REFRESH_SECRET_KEY: Optional[str] = None  # 若不設定會 fallback 為 SECRET_KEY
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # Access 1 小時
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # Refresh 30 天

    # === Rate limit / Redis ===
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_WINDOW_SEC: int = 600
    RATE_LIMIT_MAX_PER_IP: int = 200
    RATE_LIMIT_MAX_PER_EMAIL_IP: int = 50

    # === Observability（預留） ===
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENV: str = "dev"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
