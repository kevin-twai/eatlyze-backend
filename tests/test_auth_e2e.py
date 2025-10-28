# tests/test_auth_e2e.py
import pytest
from httpx import AsyncClient
from app.main import app

pytestmark = pytest.mark.asyncio

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

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c

async def test_full_flow(client: AsyncClient):
    # 先確保 DB 有這個使用者（你已有 test5@example.com）
    access, refresh = await _login_pair(client, "test5@example.com", "MyStrongPass")

    r = await _me(client, access)
    assert r.status_code == 200

    # 單點登出 -> 舊 access 應失效
    r = await _logout(client, access)
    assert r.status_code == 200
    r = await _me(client, access)
    assert r.status_code in (401, 403)

    # 用 refresh 換新 pair -> 新 access 可用
    r = await _refresh(client, refresh)
    assert r.status_code == 200
    new_access = r.json()["access_token"]
    r = await _me(client, new_access)
    assert r.status_code == 200

    # 登出全部 -> new_access 立刻失效
    r = await _logout_all(client, new_access)
    assert r.status_code == 200
    r = await _me(client, new_access)
    assert r.status_code in (401, 403)
