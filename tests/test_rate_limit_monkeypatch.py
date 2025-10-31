# tests/test_rate_limit_monkeypatch.py
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.users import User

# 盡量共用專案內的雜湊；缺時用 passlib 後備（幾乎不會走到）
try:
    from app.core.security import get_password_hash  # type: ignore
except Exception:  # pragma: no cover
    from passlib.context import CryptContext
    _pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def get_password_hash(p: str) -> str:
        return _pwd.hash(p)


async def _ensure_user(email: str, password: str, name: str = "Kevin5") -> None:
    """本測試內最小種子，避免依賴其它測試先後順序。"""
    session = AsyncSessionLocal()
    try:
        res = await session.execute(select(User).where(User.email == email))
        u = res.scalar_one_or_none()
        if u is None:
            u = User(email=email, name=name, password_hash=get_password_hash(password), token_version=0)
            session.add(u)
            await session.commit()
    finally:
        await session.close()


@pytest.mark.anyio
async def test_login_rate_limited_via_monkeypatch(client: AsyncClient, monkeypatch):
    # 準備使用者
    email = "test5@example.com"
    password = "MyStrongPass"
    await _ensure_user(email, password)

    # 確保程式碼會走到 rate-limit 分支
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True, raising=False)

    # ！！關鍵！！：patch 到路由實際引用的位置，且路由端以 await 呼叫 -> 假函式必須是 async
    # auth.py 常見：from app.services.rate_limit import check_limit_and_hit
    # 所以打到 app.api.v1.endpoints.auth.check_limit_and_hit
    async def _deny(*args, **kwargs):
        return False, 60  # 不允許、建議 60 秒後再試

    monkeypatch.setattr("app.api.v1.endpoints.auth.check_limit_and_hit", _deny, raising=True)

    # 嘗試登入
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    # 你的實作可能回 429（理想），也可能用 401/403 表示拒絕；三者皆視為通過
    assert r.status_code in (401, 403, 429), r.text
