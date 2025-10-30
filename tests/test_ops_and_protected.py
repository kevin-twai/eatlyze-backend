import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

# --- Helper functions ---
async def _login_pair(client: AsyncClient, email: str, password: str):
    """模擬登入流程"""
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    data = r.json()
    return data["access_token"], data["refresh_token"]

# --- Monitoring & Health ---
async def test_metrics_and_health(client: AsyncClient):
    """測試 /metrics, /healthz, /readyz 都能正確回應"""
    r = await client.get("/metrics")
    assert r.status_code == 200
    assert "# HELP" in r.text  # Prometheus metrics 格式驗證

    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json().get("ok") is True

    r = await client.get("/readyz")
    assert r.status_code == 200
    assert r.json().get("ready") is True

# --- Protected: Meals ---
async def test_meals_requires_auth_then_ok(client: AsyncClient):
    """驗證 /meals 路由的 Auth 保護與成功回應"""
    # 未帶 Token 應被拒
    r = await client.get("/api/v1/meals/")
    assert r.status_code in (401, 403)

    # 登入取得 Token
    access, _ = await _login_pair(client, "test5@example.com", "MyStrongPass")

    # 再次請求 -> 應成功
    r = await client.get("/api/v1/meals/", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

# --- Protected: Nutrition ---
async def test_nutrition_lookup_errors_and_ok(client: AsyncClient):
    """驗證 /nutrition API 錯誤與成功流程"""
    # 未帶 Token 應該 401/403
    r = await client.get("/api/v1/nutrition/lookup?q=chicken")
    assert r.status_code in (401, 403)

    # 登入取得 Token
    access, _ = await _login_pair(client, "test5@example.com", "MyStrongPass")

    # 缺少查詢參數 -> 應回 400/422
    r = await client.get("/api/v1/nutrition/lookup", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code in (400, 422)

    # 正確查詢 -> 200 OK
    r = await client.get(
        "/api/v1/nutrition/lookup?q=chicken",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("query") == "chicken"
    assert "per100g" in data