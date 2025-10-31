import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio

async def test_refresh_missing_field(client: AsyncClient):
    r = await client.post("/api/v1/auth/refresh", json={})
    assert r.status_code in (400, 401, 422)

async def test_refresh_empty_string(client: AsyncClient):
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": ""})
    assert r.status_code in (400, 401, 422)

async def test_refresh_malformed_token(client: AsyncClient):
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": "not.a.jwt"})
    assert r.status_code in (401, 403)