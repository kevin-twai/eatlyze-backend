# app/models/__init__.py
from .users import User  # 匯入以註冊到 Base.metadata
from .token_blacklist import TokenBlacklist  # ★ 新增
