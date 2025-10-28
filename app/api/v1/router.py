# app/api/v1/router.py
from fastapi import APIRouter

# 匯入所有已定義的 endpoint 模組
from .endpoints import health, ping, users, auth

# === API v1 主路由 ===
api_router = APIRouter()

# 系統健康檢查
api_router.include_router(health.router, prefix="/health", tags=["health"])

# ping 用於連線測試
api_router.include_router(ping.router, prefix="/ping", tags=["ping"])

# 使用者相關（註冊、列表等）
api_router.include_router(users.router, prefix="/users", tags=["users"])

# 認證 / 登入 / Refresh Token
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
