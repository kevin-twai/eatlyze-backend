# app/core/config.py
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # === App Info ===
    APP_NAME: str = "Eatlyze API"
    API_V1_PREFIX: str = "/api/v1"
    ENV: str = "dev"
    DEBUG: bool = True

    # === CORS ===
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # === Database ===
    DATABASE_URL: Optional[str] = None

    # === Auth / JWT ===
    SECRET_KEY: str = "change_this_to_a_long_random_string"
    REFRESH_SECRET_KEY: Optional[str] = None  # 若不設定會 fallback 為 SECRET_KEY
    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60           # Access Token 有效時間（1 小時）
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # Refresh Token 有效時間（30 天）

    # === Pydantic Config ===
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# 初始化設定實例
settings = Settings()
