# app/schemas/user.py
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    # 僅用於建立帳號的輸入，不會在輸出 schema 中出現
    password: str

class UserRead(BaseModel):
    id: int
    email: EmailStr
    name: str
    created_at: datetime

    class Config:
        # Pydantic v2：允許從 ORM 物件轉模型
        from_attributes = True

# 若你之後需要部分更新使用者資料，可用這個（範例）
class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    # 如果未打算在此路由更新密碼，就不要放 password
    # password: Optional[str] = None  # 建議改走專用「修改密碼」API
