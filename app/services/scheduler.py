# app/services/scheduler.py
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from fastapi import FastAPI  # ← 新增：型別標註用

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.db.session import get_db
from app.services.blacklist_cleanup import cleanup_expired_blacklist

logger = logging.getLogger(__name__)

scheduler: Optional[AsyncIOScheduler] = None

@asynccontextmanager
async def lifespan_scheduler(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan：啟動 / 關閉 APScheduler。
    需接受 app 參數（FastAPI 會注入），否則會出現 TypeError。
    """
    global scheduler
    scheduler = AsyncIOScheduler(timezone="UTC")
    # 每 30 分鐘跑一次清理黑名單
    scheduler.add_job(run_cleanup_job, IntervalTrigger(minutes=30))
    scheduler.start()
    logger.info("APScheduler started: blacklist cleanup every 30 minutes")
    try:
        yield
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)
            logger.info("APScheduler shutdown")

async def run_cleanup_job():
    """排程作業：建立一次性 DB session 來清理過期黑名單。"""
    agen = get_db()  # async generator
    db = await agen.__anext__()  # 取得 AsyncSession
    try:
        deleted = await cleanup_expired_blacklist(db)
        await db.commit()
        logger.info("Blacklist cleanup done", extra={"deleted": deleted})
    except Exception as e:
        logger.exception("Blacklist cleanup failed: %s", e)
        try:
            await db.rollback()
        except Exception:
            pass
    finally:
        # 正確關閉 get_db() 的 async generator
        try:
            await agen.aclose()
        except Exception:
            try:
                await agen.__anext__()
            except StopAsyncIteration:
                pass
