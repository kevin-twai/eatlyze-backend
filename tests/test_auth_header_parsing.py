# tests/test_auth_header_parsing.py
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio

async def test_missing_authorization_header(client: AsyncClient):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code in (401, 403)

async def test_malformed_bearer_header(client: AsyncClient):
    # 缺少 'Bearer ' 前綴
    r = await client.get("/api/v1/auth/me", headers={"Authorization": "token-only"})
    assert r.status_code in (401, 403)