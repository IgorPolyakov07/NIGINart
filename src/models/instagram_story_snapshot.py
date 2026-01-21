from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models.base import Base, TimestampMixin, UUIDMixin
if TYPE_CHECKING:
    from src.models.account import Account
class InstagramStorySnapshot(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "instagram_story_snapshots"
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to Instagram account",
    )
    story_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Instagram story media ID (from Graph API)",
    )
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Timestamp of this snapshot collection",
    )
    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the story was originally posted",
    )
    retention_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When story will expire (posted_at + 24 hours)",
    )
    media_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Story media type (IMAGE or VIDEO)",
    )
    media_url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="Media URL (if available, may expire with story)",
    )
    reach: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Unique accounts that saw this story",
    )
    impressions: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total views of this story (includes multiple views by same user)",
    )
    exits: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of times users exited this story",
    )
    replies: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of direct message replies",
    )
    taps_forward: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of taps to next story",
    )
    taps_back: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of taps to previous story",
    )
    completion_rate: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Percentage of viewers who watched to completion (calculated)",
    )
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional story metadata and insights",
    )
    account: Mapped["Account"] = relationship(
        "Account",
        backref="story_snapshots",
    )
    __table_args__ = (
        Index("idx_story_snapshots_story_id_collected", "story_id", "collected_at"),
        Index(
            "idx_story_snapshots_account_retention",
            "account_id",
            "retention_expires_at",
        ),
    )
    def __repr__(self) -> str:
        return f"<InstagramStorySnapshot {self.story_id} at {self.collected_at}>"
