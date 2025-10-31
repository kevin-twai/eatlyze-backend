# tests/conftest.py
import asyncio
import os
import importlib
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# ---- 測試期環境變數（先於 app 載入）----
os.environ.setdefault("RATE_LIMIT_ENABLED", "0")
os.environ.setdefault("ENV", "test")

from app.main import app  # noqa: E402
from app.db.session import engine  # noqa: E402

# ---- 嘗試多種路徑取得 metadata ----
_CANDIDATES = [
    ("app.db.base", "Base"),
    ("app.db.models", "Base"),
    ("app.models.base", "Base"),
    ("app.models", "Base"),
    ("app.db.session", "Base"),
    # 如果沒有 Base，嘗試模型類別
    ("app.db.models", "User"),
    ("app.db.models.user", "User"),
    ("app.models", "User"),
    ("app.models.user", "User"),
]

metadata = None
errors = []

for mod_name, attr in _CANDIDATES:
    try:
        mod = importlib.import_module(mod_name)
        if hasattr(mod, attr):
            obj = getattr(mod, attr)
            metadata = getattr(obj, "metadata", None)
            if metadata is not None:
                break
    except Exception as e:  # 記錄但不中斷
        errors.append(f"{mod_name}:{attr} -> {type(e).__name__}: {e}")

if metadata is None:
    tried = "\n  - ".join([f"{m}:{a}" for m, a in _CANDIDATES])
    detail = "\n".join(errors[-5:])
    raise ImportError(
        "找不到資料庫 metadata；請確認至少有下列任一可用：\n"
        f"  - {tried}\n"
        f"最近的錯誤摘要：\n{detail}"
    )


@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    """測試前自動 create_all，測試後 drop_all（用 asyncio.run 避免事件圈衝突）。"""
    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

    async def drop_models():
        async with engine.begin() as conn:
            await conn.run_sync(metadata.drop_all)

    asyncio.run(init_models())
    yield
    asyncio.run(drop_models())


@pytest.fixture(scope="session", autouse=True)
def close_redis_if_enabled():
    """
    若啟用 rate limit（RATE_LIMIT_ENABLED=1/true），在整個測試 session 結束時
    乾淨關閉 Redis 連線，避免 'Event loop is closed' 類殘留噪音。
    """
    yield  # 測試執行
    enabled = os.getenv("RATE_LIMIT_ENABLED", "0").lower() not in ("0", "false", "no")
    if not enabled:
        return
    try:
        # 延遲匯入，避免在沒用到時產生依賴
        from app.services.rate_limit import get_redis  # type: ignore
    except Exception:
        return

    async def _close():
        try:
            r = await get_redis()
            if hasattr(r, "close"):
                await r.close()  # type: ignore
            pool = getattr(r, "connection_pool", None)
            if pool and hasattr(pool, "disconnect"):
                await pool.disconnect()  # type: ignore
        except Exception:
            pass

    # 用新的 loop 來做收尾，避免 pytest 的 loop 已關
    asyncio.run(_close())


@pytest.fixture(scope="session")
def anyio_backend():
    """讓 pytest 使用 asyncio event loop。"""
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    """使用 ASGITransport 直接掛載 app，不需啟動伺服器。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
