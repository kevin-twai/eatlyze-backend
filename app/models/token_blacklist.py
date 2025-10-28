# app/models/token_blacklist.py
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # JWT ID（唯一），用來識別單一 token
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    # access / refresh（目前我們至少會黑名單 access）
    token_type: Mapped[str] = mapped_column(String(16), nullable=False)
    # 方便稽核（不做外鍵限制也可，但這裡用 ForeignKey 可更嚴謹）
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    # 黑名單原因（例如 logout / logout_all / admin_revoke）
    reason: Mapped[str] = mapped_column(String(255), nullable=True)

    # 到期時間（用來定期清理過期黑名單）
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("jti", name="uq_token_blacklist_jti"),
    )
