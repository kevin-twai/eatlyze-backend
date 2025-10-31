# tests/test_auth_negative.py
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio

async def test_login_wrong_password(client: AsyncClient):
    # 帳號存在但密碼錯誤 → 應 401/403
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": "test5@example.com", "password": "WrongPass"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code in (401, 403)