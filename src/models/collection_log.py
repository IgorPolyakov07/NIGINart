from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from src.models.base import Base, UUIDMixin
class CollectionLog(Base, UUIDMixin):
    __tablename__ = "collection_logs"
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Collection start time",
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Collection end time",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Status: success, partial, failed",
    )
    accounts_processed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of accounts successfully processed",
    )
    accounts_failed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of accounts that failed",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if collection failed",
    )
    def __repr__(self) -> str:
        return f"<CollectionLog {self.status} at {self.started_at}>"
