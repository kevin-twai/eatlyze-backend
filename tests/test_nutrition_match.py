# tests/test_nutrition_match.py
import pytest
from httpx import AsyncClient
try:
    # httpx >=0.28
    from httpx import ASGITransport
except ImportError:
    ASGITransport = None  # type: ignore

from app.main import app


def _make_client():
    """
    建立可相容不同 httpx 版本的 AsyncClient：
    - 新版：使用 ASGITransport(app=app)
    - 舊版（若仍支援 app 參數）：退而求其次用 AsyncClient(app=app)
    """
    if ASGITransport is not None:
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://testserver")
    # 極少數舊版 fallback（但你目前顯然不是舊版）
    return AsyncClient(app=app, base_url="http://testserver")  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_nutrition_match_basic(monkeypatch):
    # 1️⃣ monkeypatch 假查表邏輯（模擬 TFND）
    from app.api.v1.endpoints import nutrition as nutrition_ep

    def fake_match_and_calc(canonical: str, grams: float):
        assert isinstance(canonical, str) and len(canonical) > 0
        per100 = {"kcal": 165.0, "protein_g": 31.0, "fat_g": 3.6, "carb_g": 0.0}
        ratio = grams / 100.0
        total = {k: round(v * ratio, 4) for k, v in per100.items()}
        return {"per100g": per100, "total": total}

    monkeypatch.setattr(nutrition_ep, "_match_and_calc", fake_match_and_calc, raising=True)

    # 2️⃣ 呼叫 API（用相容版 client）
    async with _make_client() as ac:
        r = await ac.post(
            "/api/v1/nutrition/match",
            json={"label": "Grilled Chicken", "grams": 150},
        )
    assert r.status_code == 200, r.text
    data = r.json()

    # 3️⃣ 驗證回應格式
    assert data["canonical"] == "chicken breast"
    assert data["grams"] == 150
    assert data["confidence"] == 1.0
    # 映射命中屬於「exact/alias」其中之一（我們將 alias 歸為 exact）
    assert data["matched_from"] in ("alias", "exact")

    per100 = data["nutrition_per_100g"]
    total = data["nutrition_total"]

    assert per100 == {"kcal": 165.0, "protein_g": 31.0, "fat_g": 3.6, "carb_g": 0.0}
    assert total["kcal"] == pytest.approx(247.5, rel=1e-3)
    assert total["protein_g"] == pytest.approx(46.5, rel=1e-3)
    assert total["fat_g"] == pytest.approx(5.4, rel=1e-3)
    assert total["carb_g"] == pytest.approx(0.0, rel=1e-3)


@pytest.mark.anyio
async def test_nutrition_match_400_on_blank_label():
    async with _make_client() as ac:
        r = await ac.post("/api/v1/nutrition/match", json={"label": "   ", "grams": 100})
    assert r.status_code == 400
