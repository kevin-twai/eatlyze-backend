# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

# === Password Hashing ===
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__ident="2b",
    # 若密碼超過 72 bytes，不拋錯（與現有流程相容）
    bcrypt__truncate_error=False,
)

def _sanitize_password(p: str) -> str:
    # bcrypt 只吃前 72 bytes，避免極長密碼在某些環境報錯
    return p[:72] if isinstance(p, str) else p

def hash_password(plain: str) -> str:
    return pwd_context.hash(_sanitize_password(plain))

def verify_password(plain: str, password_hash: str) -> bool:
    return pwd_context.verify(_sanitize_password(plain), password_hash)

# === JWT Helpers ===
def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _exp(minutes: int) -> datetime:
    return _now_utc() + timedelta(minutes=minutes)

def _refresh_secret() -> str:
    # 若沒有設定 REFRESH_SECRET_KEY，會 fallback 至 SECRET_KEY（相容）
    return settings.REFRESH_SECRET_KEY or settings.SECRET_KEY

def _encode(claims: Dict[str, Any], key: str) -> str:
    return jwt.encode(claims, key, algorithm=settings.JWT_ALGORITHM)

def _decode(token: str, key: str) -> Dict[str, Any]:
    return jwt.decode(token, key, algorithms=[settings.JWT_ALGORITHM])

# === Issue Tokens ===
def create_access_token(data: Dict[str, Any], expires_minutes: Optional[int] = None) -> str:
    """
    簽發 Access Token（加入: type=access, jti, iat, exp）
    呼叫方請在 data 內帶入：
      - sub: 使用者 ID (str)
      - ver: 使用者 token_version (int)
    """
    to_encode = data.copy()
    to_encode.update({
        "type": "access",
        "jti": str(uuid4()),
        "iat": int(_now_utc().timestamp()),
        "exp": _exp(expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    })
    return _encode(to_encode, settings.SECRET_KEY)

def create_refresh_token(data: Dict[str, Any], expires_minutes: Optional[int] = None) -> str:
    """
    簽發 Refresh Token（加入: type=refresh, jti, iat, exp）
    使用 REFRESH_SECRET_KEY；若未設定則回退到 SECRET_KEY。
    呼叫方請在 data 內帶入：
      - sub: 使用者 ID (str)
      - ver: 使用者 token_version (int)
    """
    to_encode = data.copy()
    to_encode.update({
        "type": "refresh",
        "jti": str(uuid4()),
        "iat": int(_now_utc().timestamp()),
        "exp": _exp(expires_minutes or settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    })
    return _encode(to_encode, _refresh_secret())

def issue_token_pair(user_id: int, ver: int) -> Tuple[str, str]:
    """
    一次發出 Access/Refresh；ver = 使用者的 token_version
    回傳：(access_token, refresh_token)
    """
    base = {"sub": str(user_id), "ver": int(ver)}
    return create_access_token(base), create_refresh_token(base)

# === Verify / Decode ===
def decode_access_token(token: str) -> Dict[str, Any]:
    """
    驗證並解出 Access Token；若 token type 不為 access，會拋錯。
    """
    payload = _decode(token, settings.SECRET_KEY)
    if payload.get("type") != "access":
        raise JWTError("Invalid token type for this endpoint (need access token).")
    return payload

def decode_refresh_token(token: str) -> Dict[str, Any]:
    """
    驗證並解出 Refresh Token；若 token type 不為 refresh，會拋錯。
    """
    payload = _decode(token, _refresh_secret())
    if payload.get("type") != "refresh":
        raise JWTError("Invalid token type for refresh.")
    return payload

def try_decode_any(token: str) -> Dict[str, Any]:
    """
    工具函式：嘗試用 access/refresh 兩把 key 都解（診斷/除錯用）。
    """
    try:
        return _decode(token, settings.SECRET_KEY)
    except Exception:
        return _decode(token, _refresh_secret())
