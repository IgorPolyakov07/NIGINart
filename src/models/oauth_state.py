from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from src.models.base import Base
class OAuthState(Base):
    __tablename__ = "oauth_states"
    state: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        nullable=False,
        comment="CSRF protection token (UUID)",
    )
    platform: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Platform name (tiktok, instagram, etc.)",
    )
    user_identifier: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Optional user ID for multi-user scenarios",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="State creation timestamp",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Expiration timestamp (TTL = 10 minutes)",
    )
    is_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="One-time use protection flag",
    )
    def __repr__(self) -> str:
        return f"<OAuthState {self.platform}:{self.state[:8]}...>"
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
    @property
    def is_valid(self) -> bool:
        return not self.is_expired and not self.is_used
