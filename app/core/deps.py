# app/core/deps.py
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.session import get_db
from app.models.users import User
from app.models.token_blacklist import TokenBlacklist
from app.core.security import decode_access_token  # 統一用 security 的解碼


# OAuth2 Password Flow 設定
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=True,
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    從 Bearer Access Token 解析目前使用者，並做進階驗證：
      1️⃣ 驗證 JWT 與 exp
      2️⃣ 確認 token.type == "access"
      3️⃣ 驗證黑名單（是否已被登出）
      4️⃣ 依 sub 查 DB 取得 User
      5️⃣ 比對 ver == user.token_version，確保未被「全部登出」
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        if payload.get("type") != "access":
            raise unauthorized

        sub = payload.get("sub")
        if not sub:
            raise unauthorized
        user_id = int(sub)

        jti = payload.get("jti")
        ver_in_token = payload.get("ver")
    except Exception:
        raise unauthorized

    # --- 黑名單檢查 ---
    if jti:
        q = select(TokenBlacklist).where(TokenBlacklist.jti == jti)
        result = await db.execute(q)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked (blacklisted)",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # --- 取得使用者 ---
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise unauthorized

    # --- 版本比對（防止舊 token）---
    try:
        user_token_version = int(getattr(user, "token_version", 0))
        if ver_in_token is None or int(ver_in_token) != user_token_version:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalidated by global logout",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception:
        raise unauthorized

    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    不強制登入：
      - 有帶且有效 -> 回傳 User
      - 沒帶 / 無效 -> 回傳 None
    """
    if not token:
        return None

    try:
        payload = decode_access_token(token)
        if payload.get("type") != "access":
            return None

        sub = payload.get("sub")
        if not sub:
            return None
        user_id = int(sub)

        jti = payload.get("jti")
        ver_in_token = payload.get("ver")
    except Exception:
        return None

    # 黑名單檢查
    if jti:
        q = select(TokenBlacklist).where(TokenBlacklist.jti == jti)
        result = await db.execute(q)
        if result.scalar_one_or_none():
            return None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None

    try:
        user_token_version = int(getattr(user, "token_version", 0))
        if ver_in_token is None or int(ver_in_token) != user_token_version:
            return None
    except Exception:
        return None

    return user
