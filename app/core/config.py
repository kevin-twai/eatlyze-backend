# app/core/config.py
from __future__ import annotations

from functools import lru_cache
from typing import Any, List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # === App Info ===
    APP_NAME: str = "Eatlyze API"
    API_V1_PREFIX: str = "/api/v1"
    ENV: str = "dev"
    DEBUG: bool = True

    # === CORS ===
    # 統一以字串清單處理；.env 可給 JSON 或逗號分隔字串
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                import json
                return [x.strip() for x in json.loads(s)]
            return [x.strip() for x in s.split(",") if x.strip()]
        return v

    # === Database ===
    DATABASE_URL: str = "postgresql+asyncpg://eatlyze:eatlyze@localhost:5432/eatlyze"
    DB_ECHO: bool = False

    # === Auth / JWT ===
    SECRET_KEY: str = "change_this_to_a_long_random_string"
    REFRESH_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30

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
