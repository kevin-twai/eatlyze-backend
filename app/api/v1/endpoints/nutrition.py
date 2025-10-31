# app/api/v1/endpoints/nutrition.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.core.deps import get_current_user
from app.models.users import User
from app.ml.food_features import extract_features

router = APIRouter(tags=["nutrition"])

# ===========================================
# 原有功能：受保護的 /lookup
# ===========================================
@router.get("/lookup", summary="Lookup nutrition (protected)")
async def nutrition_lookup(
    q: str = Query(..., description="食材/餐點查詢字串"),
    current_user: User = Depends(get_current_user),
):
    if not q:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="q is required")
    # TODO: 串接營養庫；先回假資料
    return {"query": q, "per100g": {"kcal": 165, "protein_g": 31}}


# ===========================================
# Phase 2 新增：/match 端點
# ===========================================
class MatchRequest(BaseModel):
    label: str = Field(..., description="原始食物名稱（Vision 或手動輸入）")
    grams: float = Field(..., gt=0, description="總重量（g）")


class NutritionBlock(BaseModel):
    kcal: float = 0
    protein_g: float = 0
    fat_g: float = 0
    carb_g: float = 0


class MatchResponse(BaseModel):
    canonical: str
    confidence: float
    matched_from: str
    grams: float
    nutrition_per_100g: NutritionBlock
    nutrition_total: NutritionBlock


def _match_and_calc_default(canonical: str, grams: float) -> Dict[str, Any]:
    """
    預設：回傳假資料；待接上 TFND/DB 查表後替換。
    """
    try:
        raise ImportError  # 暫時跳過真實查表
    except Exception:
        per100 = {"kcal": 0.0, "protein_g": 0.0, "fat_g": 0.0, "carb_g": 0.0}

    ratio = grams / 100.0
    total = {k: round(v * ratio, 4) for k, v in per100.items()}
    return {"per100g": per100, "total": total}


_match_and_calc = _match_and_calc_default


@router.post("/match", response_model=MatchResponse, summary="Match food label to TFND nutrition values")
async def nutrition_match(payload: MatchRequest):
    if not payload.label.strip():
        raise HTTPException(status_code=400, detail="label is empty")

    features = extract_features(payload.label)
    canonical = features["canonical"]
    confidence = float(features["confidence"])
    matched_from = str(features["matched_from"])

    calc = _match_and_calc(canonical, payload.grams)
    per100 = calc["per100g"]
    total = calc["total"]

    return MatchResponse(
        canonical=canonical,
        confidence=confidence,
        matched_from=matched_from,
        grams=payload.grams,
        nutrition_per_100g=NutritionBlock(**per100),
        nutrition_total=NutritionBlock(**total),
    )
