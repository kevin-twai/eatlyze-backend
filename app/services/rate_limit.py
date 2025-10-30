# app/services/rate_limit.py
from __future__ import annotations

import os
import time
from typing import Optional, Tuple

from redis.asyncio import Redis
from app.core.config import settings as _settings

# ---- 參數（帶防呆預設）----
REDIS_URL: str = getattr(_settings, "REDIS_URL", "redis://localhost:6379/0")
WINDOW_SEC: int = int(getattr(_settings, "RATE_LIMIT_WINDOW_SEC", 600))
MAX_PER_IP: int = int(getattr(_settings, "RATE_LIMIT_MAX_PER_IP", 200))
MAX_PER_EMAIL_IP: int = int(getattr(_settings, "RATE_LIMIT_MAX_PER_EMAIL_IP", 50))

# ---- 開關：可由 env 或 settings 控制；pytest 自動停用 ----
def _is_pytest() -> bool:
    return bool(
        os.getenv("PYTEST_CURRENT_TEST")  # pytest 會設
        or os.getenv("PYTEST") in ("1", "true", "True")
        or getattr(_settings, "TESTING", False)
    )

_RATE_LIMIT_ENABLED: bool = str(getattr(_settings, "RATE_LIMIT_ENABLED", "1")) not in ("0", "false", "False")
_DISABLE_FOR_TEST: bool = _is_pytest()

def _enabled() -> bool:
    # 測試時一律停用；否則看總開關
    return _RATE_LIMIT_ENABLED and not _DISABLE_FOR_TEST

# 單例 Redis（lazy-init）
_redis: Optional[Redis] = None

def _get_redis() -> Redis:
    """Lazy 初始化 Redis 連線。只有在限流啟用時才會被呼叫。"""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis

def _key_ip(ip: str) -> str:
    return f"rl:login:ip:{ip or 'unknown'}"

def _key_email_ip(email: str, ip: str) -> str:
    return f"rl:login:ei:{(email or '').lower()}|{ip or 'unknown'}"

async def _prune(redis: Redis, key: str, now_s: float) -> None:
    await redis.zremrangebyscore(key, "-inf", now_s - WINDOW_SEC)

async def _count(redis: Redis, key: str) -> int:
    return int(await redis.zcard(key))

async def _oldest_ts(redis: Redis, key: str) -> Optional[float]:
    data = await redis.zrange(key, 0, 0, withscores=True)
    if data:
        return float(data[0][1])
    return None

async def _hit(redis: Redis, key: str, now_s: float) -> None:
    member = f"{now_s:.3f}"
    await redis.zadd(key, {member: now_s})

async def check_limit_and_hit(ip: str, email: Optional[str]) -> Tuple[bool, int]:
    """
    檢查是否超出限流；若允許會記一次嘗試。
    測試或總開關關閉時，直接放行且不觸碰 Redis。
    """
    if not _enabled():
        return True, 0

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
    登入成功後清空 email+IP 的桶；測試或關閉時直接略過。
    """
    if not email or not _enabled():
        return
    r = _get_redis()
    await r.delete(_key_email_ip(email, ip))
