# app/api/v1/endpoints/users.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.users import User
from app.schemas.user import UserCreate, UserRead
from app.core.security import hash_password
from app.core.deps import get_current_user  # 保護需要登入的路由

router = APIRouter(tags=["users"])

# === 註冊（開放） ===
@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    # 檢查 email 是否已存在
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )

    # 建立新使用者（雜湊密碼）
    user = User(
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

# === 取得使用者列表（需要登入） ===
@router.get("/", response_model=List[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),  # 需要 Bearer Token；用 "_" 表示僅驗證不使用變數
):
    result = await db.execute(select(User).order_by(User.id))
    return result.scalars().all()

# === 取得目前登入者（需要登入） ===
@router.get("/me", response_model=UserRead)
async def users_me(current_user: User = Depends(get_current_user)):
    return current_user
