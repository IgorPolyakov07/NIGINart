from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models.base import Base, TimestampMixin, UUIDMixin
if TYPE_CHECKING:
    from src.models.metric import Metric
class Account(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "accounts"
    platform: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Platform name (instagram, telegram, youtube, etc.)",
    )
    account_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Platform-specific account identifier",
    )
    account_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Full URL to the account",
    )
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable account name",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether data collection is enabled",
    )
    encrypted_access_token: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Encrypted OAuth access token (Fernet AES-128)",
    )
    encrypted_refresh_token: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Encrypted OAuth refresh token (Fernet AES-128)",
    )
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="OAuth token expiration timestamp (for auto-refresh)",
    )
    token_scope: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="OAuth token scopes (comma-separated)",
    )
    advertiser_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="TikTok advertiser ID for Marketing API",
    )
    metrics: Mapped[list["Metric"]] = relationship(
        "Metric",
        back_populates="account",
        cascade="all, delete-orphan",
    )
    def __repr__(self) -> str:
        return f"<Account {self.platform}:{self.account_id}>"
