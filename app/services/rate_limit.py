# app/services/rate_limit.py
from collections import deque
from time import time
from typing import Deque, Dict, Tuple

# key: (ip, email) -> timestamps
_BUCKETS: Dict[Tuple[str, str], Deque[float]] = {}
WINDOW_SEC = 5 * 60
MAX_HITS = 5

def allow(ip: str, email: str) -> bool:
    now = time()
    key = (ip, email.lower())
    q = _BUCKETS.setdefault(key, deque())
    # 移除過窗資料
    while q and now - q[0] > WINDOW_SEC:
        q.popleft()
    if len(q) >= MAX_HITS:
        return False
    q.append(now)
    return True