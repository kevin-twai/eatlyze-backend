# app/api/v1/endpoints/nutrition.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.core.deps import get_current_user
from app.models.users import User

router = APIRouter(tags=["nutrition"])

@router.get("/lookup", summary="Lookup nutrition (protected)")
async def nutrition_lookup(
    q: str = Query(..., description="食材/餐點查詢字串"),
    current_user: User = Depends(get_current_user),
):
    if not q:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="q is required")
    # TODO: 串接營養庫；先回假資料
    return {"query": q, "per100g": {"kcal": 165, "protein_g": 31}}