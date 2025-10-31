# app/db/session.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# ---- Engine ----
DATABASE_URL = settings.DATABASE_URL or "postgresql+asyncpg://eatlyze:eatlyze@localhost:5432/eatlyze"
echo_flag = str(getattr(settings, "DB_ECHO", "false")).lower() in {"1", "true", "yes"}

# pool_pre_ping 讓連線池自我檢查、future=True 取用新式行為
engine = create_async_engine(
    DATABASE_URL,
    echo=echo_flag,
    pool_pre_ping=True,
    future=True,
)

# ---- Session factory ----
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ---- Dependency ----
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依賴：產生一個 AsyncSession，並在完成後總是關閉。
    以 try/finally 強制 close，避免 GC 回收時出現 non-checked-in 連線警告。
    """
    session: AsyncSession = AsyncSessionLocal()
    try:
        yield session
    finally:
        try:
            await session.close()
        except Exception:
            # 測試或關機階段若事件圈已關閉，避免拋出次要錯誤
            pass
