# app/api/v1/endpoints/meals.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.deps import get_current_user
from app.models.users import User

router = APIRouter(tags=["meals"])

@router.get("/", summary="List meals (protected)")
async def list_meals(current_user: User = Depends(get_current_user)):
    # TODO: 串接 DB；先回假資料
    return [{"id": 1, "name": "Chicken Salad", "kcal": 420}]

@router.post("/", summary="Create a meal (protected)")
async def create_meal(item: dict, current_user: User = Depends(get_current_user)):
    if not item.get("name"):
        # 後續可改為統一錯誤結構（app/core/errors.py）
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required")
    # TODO: 寫入 DB；先回假資料
    return {"id": 2, **item}