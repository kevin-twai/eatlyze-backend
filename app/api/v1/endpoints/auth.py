# app/api/v1/endpoints/auth.py
from typing import Dict, Optional, Tuple, List
import time
from datetime import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.users import User
from app.models.token_blacklist import TokenBlacklist
from app.core.deps import get_current_user
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    try_decode_any,  # 取出 jti/exp/type/sub 用
)
from app.schemas.auth import TokenPair, RefreshRequest
from app.schemas.user import UserRead

router = APIRouter(tags=["auth"])

# =========================
# 簡版 Rate Limit（無套件）
# =========================
# 規則：同一 IP 每 10 分鐘最多 20 次登入請求；同一 email+IP 每 10 分鐘最多 5 次
RATE_WINDOW_SECONDS = 10 * 60
RATE_MAX_ATTEMPTS_IP = 20
RATE_MAX_ATTEMPTS_EMAIL_IP = 5

# in-memory 紀錄（多實例/重啟會重置；正式可改 Redis）
_rate_buckets_ip: Dict[str, List[float]] = {}
_rate_buckets_email_ip: Dict[str, List[float]] = {}

def _prune_and_count(bucket: List[float], now: float) -> int:
    """移除已過窗的紀錄，回傳窗口內的次數"""
    threshold = now - RATE_WINDOW_SECONDS
    while bucket and bucket[0] < threshold:
        bucket.pop(0)
    return len(bucket)

def _hit(bucket: List[float], now: float) -> None:
    bucket.append(now)

def _check_rate_limit(ip: str, email: Optional[str]) -> Tuple[bool, int]:
    """
    回傳 (允許通過, 建議 Retry-After 秒數)
    - 先檢查 IP，後檢查 email+IP
    """
    now = time.time()

    # ---- IP 維度 ----
    b_ip = _rate_buckets_ip.setdefault(ip, [])
    cnt_ip = _prune_and_count(b_ip, now)
    if cnt_ip >= RATE_MAX_ATTEMPTS_IP:
        retry_after = int(max(1, RATE_WINDOW_SECONDS - (now - b_ip[0])))
        return False, retry_after

    # ---- email+IP 維度（避免帳號被暴力猜測）----
    if email:
        key = f"{email.lower()}|{ip}"
        b_ei = _rate_buckets_email_ip.setdefault(key, [])
        cnt_ei = _prune_and_count(b_ei, now)
        if cnt_ei >= RATE_MAX_ATTEMPTS_EMAIL_IP:
            retry_after = int(max(1, RATE_WINDOW_SECONDS - (now - b_ei[0])))
            return False, retry_after

    return True, 0

def _record_attempt(ip: str, email: Optional[str]) -> None:
    now = time.time()
    _hit(_rate_buckets_ip.setdefault(ip, []), now)
    if email:
        key = f"{email.lower()}|{ip}"
        _hit(_rate_buckets_email_ip.setdefault(key, []), now)

def _reset_success(ip: str, email: Optional[str]) -> None:
    """登入成功後，可選擇清空 email+IP 的紀錄，降低誤鎖風險（IP 維度保留，以防掃號）"""
    if email:
        key = f"{email.lower()}|{ip}"
        _rate_buckets_email_ip.pop(key, None)


def _extract_jti_and_exp(token: str) -> Tuple[Optional[str], Optional[int], Optional[str], Optional[str]]:
    """從任一 JWT 取出 (jti, exp, type, sub)，exp 為 epoch 秒"""
    try:
        claims = try_decode_any(token)
        jti = claims.get("jti")
        exp = claims.get("exp")
        typ = claims.get("type")
        sub = claims.get("sub")
        if exp is not None and not isinstance(exp, int):
            try:
                exp = int(getattr(exp, "timestamp")())  # 某些 jose 會給 datetime
            except Exception:
                exp = None
        return jti, exp, typ, sub
    except Exception:
        return None, None, None, None


# === 登入（含 Rate Limit） ===
@router.post("/login", response_model=TokenPair)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    使用者登入，簽發 Access / Refresh。
    security.py 會自動加入 type、jti、ver、exp。
    *新增：Rate Limit（以 IP 與 email+IP 控制暴力嘗試）*
    """
    ip = (request.client.host if request.client else "unknown") or "unknown"
    email = (form_data.username or "").strip()
    allow, retry_after = _check_rate_limit(ip, email)
    if not allow:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    # 記一次嘗試（成功或失敗都算一次）
    _record_attempt(ip, email)

    password = form_data.password
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        # 統一訊息避免帳號探測
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # ✅ 登入成功後清空 email+IP 的嘗試（避免誤鎖）
    _reset_success(ip, email)

    # ✅ 帶入當前 token_version 作為 ver
    access_token = create_access_token({"sub": str(user.id), "ver": user.token_version})
    refresh_token = create_refresh_token({"sub": str(user.id), "ver": user.token_version})

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


# === Refresh Token 兌換（舊 refresh 黑名單化 + ver 比對） ===
@router.post("/refresh", response_model=TokenPair)
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        claims = decode_refresh_token(payload.refresh_token)
        if claims.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")
        user_id = claims.get("sub")
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid token payload")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # 取得使用者的當前版本號（ver）
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # 🔒 關鍵補強：refresh 的 ver 必須與目前 user.token_version 一致
    token_ver = claims.get("ver")
    if token_ver is None or int(token_ver) != int(user.token_version):
        # 一律以同樣的訊息回覆，避免側錄到版本資訊
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # 帶入當前 token_version 簽發新 pair
    new_access = create_access_token({"sub": str(user.id), "ver": user.token_version})
    new_refresh = create_refresh_token({"sub": str(user.id), "ver": user.token_version})

    # 黑名單舊 refresh
    old_jti, old_exp, old_type, _ = _extract_jti_and_exp(payload.refresh_token)
    if old_jti and old_exp:
        db.add(TokenBlacklist(
            jti=old_jti,
            token_type=old_type or "refresh",
            user_id=int(user.id),
            expires_at=dt.utcfromtimestamp(old_exp),
        ))
        await db.commit()

    return TokenPair(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
    )


# === 單次登出 ===
@router.post("/logout", response_model=dict)
async def logout(
    current_user: User = Depends(get_current_user),
    authorization: Optional[str] = Header(None),
    payload: Optional[RefreshRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """單次登出：將 access / refresh 加入黑名單"""
    if authorization and authorization.lower().startswith("bearer "):
        access_token = authorization.split(" ", 1)[1].strip()
        a_jti, a_exp, a_type, _ = _extract_jti_and_exp(access_token)
        if a_jti and a_exp:
            db.add(TokenBlacklist(
                jti=a_jti,
                token_type=a_type or "access",
                user_id=current_user.id,
                expires_at=dt.utcfromtimestamp(a_exp),
            ))

    if payload and payload.refresh_token:
        r_jti, r_exp, r_type, _ = _extract_jti_and_exp(payload.refresh_token)
        if r_jti and r_exp:
            db.add(TokenBlacklist(
                jti=r_jti,
                token_type=r_type or "refresh",
                user_id=current_user.id,
                expires_at=dt.utcfromtimestamp(r_exp),
            ))

    await db.commit()
    return {"detail": "Logged out"}


# === 登出全部 ===
@router.post("/logout-all", response_model=dict)
async def logout_all(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    """
    全部登出：
      - token_version 自增 → 舊 token 全失效
      - 將目前 access jti 加入黑名單
    """
    current_user.token_version = int(getattr(current_user, "token_version", 0)) + 1
    await db.commit()
    await db.refresh(current_user)

    if authorization and authorization.lower().startswith("bearer "):
        access_token = authorization.split(" ", 1)[1].strip()
        a_jti, a_exp, a_type, _ = _extract_jti_and_exp(access_token)
        if a_jti and a_exp:
            db.add(TokenBlacklist(
                jti=a_jti,
                token_type=a_type or "access",
                user_id=current_user.id,
                expires_at=dt.utcfromtimestamp(a_exp),
            ))
            await db.commit()

    return {"detail": "Logged out from all devices"}


# === 驗證 Token ===
@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/test-token", response_model=dict)
async def test_token(current_user: User = Depends(get_current_user)) -> Dict[str, int]:
    return {"ok": True, "user_id": current_user.id}
