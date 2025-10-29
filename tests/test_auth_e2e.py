# tests/test_auth_e2e.py
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.session import get_db
from app.models.users import User

# 優先沿用專案內的密碼雜湊；若無則用 passlib 後備
try:
    from app.core.security import get_password_hash  # type: ignore
except Exception:  # pragma: no cover
    from passlib.context import CryptContext
    _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def get_password_hash(p: str) -> str:
        return _pwd_ctx.hash(p)


pytestmark = pytest.mark.asyncio


async def _ensure_user(email: str, password: str, name: str = "Kevin5") -> None:
    """
    確保測試帳號存在；沒有就建立。
    透過專案現成 get_db() 取得 AsyncSession。
    """
    async for db in get_db():
        session = db
        break

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


async def _login_pair(client: AsyncClient, email: str, password: str):
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


# ✅ 不需要自己定義 client fixture
# 會自動使用 tests/conftest.py 的 AsyncClient

async def test_full_flow(client: AsyncClient):
    """整合測試：seed → login → me → logout → refresh → logout-all"""
    email = "test5@example.com"
    password = "MyStrongPass"

    # 先 seed 使用者（CI 空 DB 也能跑）
    await _ensure_user(email, password)

    # 登入
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
    assert r.status_code == 200, r.text
    r = await _me(client, new_access)
    assert r.status_code in (401, 403)
