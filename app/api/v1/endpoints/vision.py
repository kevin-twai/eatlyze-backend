# app/api/v1/endpoints/vision.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import base64

router = APIRouter()

class VisionAnalyzeIn(BaseModel):
    image_b64: str = Field(..., description="base64-encoded image (no data: prefix needed)")

class VisionAnalyzeOut(BaseModel):
    labels: list[str]
    model: str

@router.post("/vision/analyze", response_model=VisionAnalyzeOut)
async def analyze_image(payload: VisionAnalyzeIn):
    """
    Minimal stub for Phase 2 step-1.
    - 只驗證 base64 是否可解碼
    - 回傳固定 labels（後續再接 OpenAI / 自訓模型）
    """
    try:
        # 驗證 base64
        _ = base64.b64decode(payload.image_b64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image")

    # 先回固定結構，未綁外部服務，方便寫測試與提升覆蓋率
    return VisionAnalyzeOut(labels=["rice", "chicken", "broccoli"], model="vision-mock-0")