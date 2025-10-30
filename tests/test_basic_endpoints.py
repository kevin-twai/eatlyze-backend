# tests/test_basic_endpoints.py
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio

async def test_ping_health(client: AsyncClient):
    r = await client.get("/api/v1/ping/")
    assert r.status_code == 200
    assert r.json().get("message") == "pong"

    r = await client.get("/api/v1/health/")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data and data["status"] in ("ok", "healthy", "OK")

async def test_me_unauthorized(client: AsyncClient):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code in (401, 403)