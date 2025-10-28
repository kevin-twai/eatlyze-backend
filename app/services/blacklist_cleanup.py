# app/services/blacklist_cleanup.py
from datetime import datetime, timezone
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.token_blacklist import TokenBlacklist

async def cleanup_expired_blacklist(db: AsyncSession) -> int:
    """刪除已過期的黑名單，回傳刪除數量。"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # DB 多半是 naive UTC
    stmt = delete(TokenBlacklist).where(TokenBlacklist.expires_at < now)
    res = await db.execute(stmt)
    await db.commit()
    return res.rowcount or 0