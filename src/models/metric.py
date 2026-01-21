from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID
from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models.base import Base, UUIDMixin
if TYPE_CHECKING:
    from src.models.account import Account
class Metric(Base, UUIDMixin):
    __tablename__ = "metrics"
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Timestamp when data was collected",
    )
    followers: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of followers/subscribers",
    )
    posts_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total number of posts/videos",
    )
    total_likes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total likes across recent posts",
    )
    total_comments: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total comments across recent posts",
    )
    total_views: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total views (for video platforms)",
    )
    total_shares: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total shares/reposts",
    )
    engagement_rate: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Engagement rate percentage",
    )
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional platform-specific metrics",
    )
    account: Mapped["Account"] = relationship(
        "Account",
        back_populates="metrics",
    )
    def __repr__(self) -> str:
        return f"<Metric {self.account_id} at {self.collected_at}>"
