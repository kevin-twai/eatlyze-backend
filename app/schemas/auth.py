from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPair(Token):
    refresh_token: str  # ★ 新增

class RefreshRequest(BaseModel):
    refresh_token: str
