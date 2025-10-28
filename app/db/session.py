from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL or "postgresql+asyncpg://eatlyze:eatlyze@localhost:5432/eatlyze"
engine = create_async_engine(DATABASE_URL, echo=(str(getattr(settings, "DB_ECHO", "false")).lower()=="true"))
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session