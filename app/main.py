# app/main.py
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.errors import register_error_handlers
from app.api.v1.router import api_router
from app.services.scheduler import lifespan_scheduler  # lifespan（排程）

logger = setup_logging()
log = logging.getLogger(__name__)

def _validate_secrets() -> None:
    """
    部署前安全檢查：在 prod/staging/preview 等環境時，不允許使用短或空的金鑰。
    """
    env = (settings.ENV or "").lower()
    if env in {"prod", "production", "staging", "preview"}:
        missing_or_weak = []
        if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
            missing_or_weak.append("SECRET_KEY")
        if not settings.REFRESH_SECRET_KEY or len(settings.REFRESH_SECRET_KEY) < 32:
            missing_or_weak.append("REFRESH_SECRET_KEY")
        if missing_or_weak:
            raise RuntimeError(
                f"Insecure config for {', '.join(missing_or_weak)} in ENV={settings.ENV}. "
                "Please set strong keys via environment variables."
            )

def create_app() -> FastAPI:
    # 基本安全檢查
    _validate_secrets()

    # 啟用 lifespan（內含 APScheduler：黑名單清理排程）
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan_scheduler,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 統一錯誤處理
    register_error_handlers(app)

    # API 路由
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Root 健康檢查
    @app.get("/", summary="Root")
    async def root():
        return {"app": settings.APP_NAME, "env": settings.ENV}

    log.info("Application initialized", extra={"env": settings.ENV})
    return app

# Uvicorn 進入點
app = create_app()
