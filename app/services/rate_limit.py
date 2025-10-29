# app/services/rate_limit.py
from __future__ import annotations

import time
from typing import Optional, Tuple

from redis.asyncio import Redis
from app.core.config import settings

# 讀取環境參數（.env / settings）
WINDOW_SEC: int = int(getattr(settings, "RATE_LIMIT_WINDOW_SEC", 600))
MAX_PER_IP: int = int(getattr(settings, "RATE_LIMIT_MAX_PER_IP", 200))
MAX_PER_EMAIL_IP: int = int(getattr(settings, "RATE_LIMIT_MAX_PER_EMAIL_IP", 50))

# 單例 Redis 連線（async）
_redis: Optional[Redis] = None


def _get_redis() -> Redis:
    """Lazy 初始化 Redis 連線。aioredis>=2 已合併到 redis-py（redis.asyncio）。"""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,  # 用字串好除錯
        )
    return _redis


def _key_ip(ip: str) -> str:
    return f"rl:login:ip:{ip or 'unknown'}"


def _key_email_ip(email: str, ip: str) -> str:
    return f"rl:login:ei:{(email or '').lower()}|{ip or 'unknown'}"


async def _prune(redis: Redis, key: str, now_s: float) -> None:
    """移除滑動視窗外的紀錄（分數 < now - WINDOW_SEC）。"""
    await redis.zremrangebyscore(key, "-inf", now_s - WINDOW_SEC)


async def _count(redis: Redis, key: str) -> int:
    return int(await redis.zcard(key))


async def _oldest_ts(redis: Redis, key: str) -> Optional[float]:
    """取得窗口內最舊嘗試的時間戳（若無則 None）。"""
    data = await redis.zrange(key, 0, 0, withscores=True)
    if data:
        # data 形如 [(member, score)]，我們把 score 存 epoch 秒
        return float(data[0][1])
    return None


async def _hit(redis: Redis, key: str, now_s: float) -> None:
    """記錄一次嘗試（ZSET，score=now）。"""
    member = f"{now_s:.3f}"  # 簡單用時間字串作成員，避免重複
    await redis.zadd(key, {member: now_s})


async def check_limit_and_hit(ip: str, email: Optional[str]) -> Tuple[bool, int]:
    """
    檢查是否超出限流；若允許，會「順便記一次嘗試」。
    回傳：(allowed, retry_after_seconds)
      先看 IP 維度，再看 email+IP 維度。
      若超出，retry_after = 距離最舊紀錄出窗的剩餘秒數（>=1）。
    """
    r = _get_redis()
    now_s = time.time()

    # ---- IP 維度 ----
    kip = _key_ip(ip)
    await _prune(r, kip, now_s)
    cnt_ip = await _count(r, kip)
    if cnt_ip >= MAX_PER_IP:
        oldest = await _oldest_ts(r, kip)
        retry_after = max(1, int(WINDOW_SEC - (now_s - (oldest or now_s))))
        return False, retry_after

    # ---- email+IP 維度 ----
    if email:
        kei = _key_email_ip(email, ip)
        await _prune(r, kei, now_s)
        cnt_ei = await _count(r, kei)
        if cnt_ei >= MAX_PER_EMAIL_IP:
            oldest = await _oldest_ts(r, kei)
            retry_after = max(1, int(WINDOW_SEC - (now_s - (oldest or now_s))))
            return False, retry_after

    # 允許：記錄一次嘗試
    await _hit(r, kip, now_s)
    if email:
        await _hit(r, _key_email_ip(email, ip), now_s)

    return True, 0


async def reset_success(ip: str, email: Optional[str]) -> None:
    """
    登入成功後清空 email+IP 的桶，降低誤鎖風險。
    IP 維度不清空，保留反掃號的保護力。
    """
    if not email:
        return
    r = _get_redis()
    await r.delete(_key_email_ip(email, ip))
