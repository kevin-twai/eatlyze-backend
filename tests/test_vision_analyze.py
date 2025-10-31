# tests/test_vision_analyze.py
import base64
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio

async def test_vision_analyze_minimal(client: AsyncClient):
    # 做一個可被 base64 解碼的小位元組內容（不需是真實圖片）
    fake_bytes = b"\x89PNG\r\n\x1a\n"  # 任意少量 bytes
    img_b64 = base64.b64encode(fake_bytes).decode()

    r = await client.post("/api/v1/vision/analyze", json={"image_b64": img_b64})
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data.get("labels"), list)
    assert isinstance(data.get("model"), str)
    assert len(data["labels"]) > 0

async def test_vision_analyze_invalid_b64(client: AsyncClient):
    r = await client.post("/api/v1/vision/analyze", json={"image_b64": "not-base64"})
    assert r.status_code == 400