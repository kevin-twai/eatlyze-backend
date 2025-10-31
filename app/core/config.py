# app/core/config.py
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # === App Info ===
    APP_NAME: str = "Eatlyze API"
    API_V1_PREFIX: str = "/api/v1"
    ENV: str = os.getenv("ENV", "dev")
    DEBUG: bool = True

    # === CORS ===
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
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://eatlyze:eatlyze@localhost:5432/eatlyze",
    )
    DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"

    # === Auth / JWT ===
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change_this_to_a_long_random_string")
    REFRESH_SECRET_KEY: Optional[str] = os.getenv("REFRESH_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 30)))

    # === Rate limit / Redis ===
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    RATE_LIMIT_WINDOW_SEC: int = int(os.getenv("RATE_LIMIT_WINDOW_SEC", "600"))
    RATE_LIMIT_MAX_PER_IP: int = int(os.getenv("RATE_LIMIT_MAX_PER_IP", "200"))
    RATE_LIMIT_MAX_PER_EMAIL_IP: int = int(os.getenv("RATE_LIMIT_MAX_PER_EMAIL_IP", "50"))

    # 預設行為：若偵測到 pytest，停用限流；
    # 否則依環境變數 RATE_LIMIT_ENABLED 決定。
    RATE_LIMIT_ENABLED: bool = (
        (os.getenv("PYTEST_CURRENT_TEST") is None)
        and os.getenv("RATE_LIMIT_ENABLED", "1").lower() not in ("0", "false", "no")
    )

    # === Observability（Sentry / Monitoring） ===
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
    SENTRY_ENV: str = os.getenv("SENTRY_ENV", "dev")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """測試環境自動改用 SQLite 並停用限流"""
    s = Settings()
    if s.ENV == "test":
        # 預設改用本機 SQLite DB
        if "DATABASE_URL" not in os.environ:
            s.DATABASE_URL = "sqlite+aiosqlite:///./test.db"
        # 停用 Redis 限流
        s.RATE_LIMIT_ENABLED = False
    return s


settings = get_settings()
