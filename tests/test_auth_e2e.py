# tests/test_auth_e2e.py
import time
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from jose import jwt  # 使用 python-jose

from app.db.session import AsyncSessionLocal
from app.models.users import User
from app.core.config import settings

# 優先沿用專案內的密碼雜湊；若無則用 passlib 後備
try:
    from app.core.security import get_password_hash  # type: ignore
except Exception:  # pragma: no cover
    from passlib.context import CryptContext
    _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def get_password_hash(p: str) -> str:
        return _pwd_ctx.hash(p)

pytestmark = pytest.mark.anyio


async def _ensure_user(email: str, password: str, name: str = "Kevin5") -> None:
    """確保測試帳號存在；沒有就建立。顯式關閉 DB Session，避免 SAWarning。"""
    session = AsyncSessionLocal()
    try:
        res = await session.execute(select(User).where(User.email == email))
        u = res.scalar_one_or_none()
        if u is None:
            u = User(
                email=email,
                name=name,
                password_hash=get_password_hash(password),
                token_version=0,
            )
            session.add(u)
            await session.commit()
    finally:
        await session.close()


async def _login_pair(client: AsyncClient, email: str, password: str):
    # 依你現有 API，使用 x-www-form-urlencoded（最穩）
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return data["access_token"], data["refresh_token"]


async def _me(client: AsyncClient, token: str):
    return await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})


async def _logout(client: AsyncClient, token: str):
    return await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})


async def _refresh(client: AsyncClient, refresh_token: str):
    return await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})


async def _logout_all(client: AsyncClient, token: str):
    return await client.post("/api/v1/auth/logout-all", headers={"Authorization": f"Bearer {token}"})


# ✅ 會自動使用 tests/conftest.py 的 AsyncClient
async def test_full_flow(client: AsyncClient):
    """整合測試：seed → login → me → logout → refresh → logout-all"""
    email = "test5@example.com"
    password = "MyStrongPass"

    await _ensure_user(email, password)

    access, refresh = await _login_pair(client, email, password)

    # me OK
    r = await _me(client, access)
    assert r.status_code == 200, r.text

    # 單點登出 -> 舊 access 應失效
    r = await _logout(client, access)
    assert r.status_code == 200, r.text
    r = await _me(client, access)
    assert r.status_code in (401, 403)

    # 用 refresh 換新 pair -> 新 access 可用
    r = await _refresh(client, refresh)
    assert r.status_code == 200, r.text
    new_access = r.json()["access_token"]
    r = await _me(client, new_access)
    assert r.status_code == 200, r.text

    # 登出全部 -> new_access 立刻失效
    r = await _logout_all(client, new_access)
    assert r.status_code in (200, 204), r.text
    r = await _me(client, new_access)
    assert r.status_code in (401, 403)


async def test_logout_all_invalidates_old_tokens(client: AsyncClient):
    """登出全失效後，舊 access/refresh 都應失效（打到 token_version 分支）"""
    email = "test5@example.com"
    password = "MyStrongPass"
    await _ensure_user(email, password)

    access1, refresh1 = await _login_pair(client, email, password)

    # 登出所有裝置 -> token_version +1
    r = await _logout_all(client, access1)
    assert r.status_code in (200, 204), r.text

    # 舊 access 立即失效
    r = await _me(client, access1)
    assert r.status_code in (401, 403)

    # 舊 refresh 也應失效
    r = await _refresh(client, refresh1)
    assert r.status_code in (401, 403)


async def test_jwt_decode_errors_and_expired(client: AsyncClient):
    """JWT 解析錯誤／過期（打到 decode error 與 exp 過期分支）"""
    # 亂碼 token
    r = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code in (401, 403)

    # 建一個立即過期的 token（exp = 現在-1）
    now = int(time.time())
    payload = {"sub": "1", "exp": now - 1, "iat": now - 2}
    expired = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code in (401, 403)
