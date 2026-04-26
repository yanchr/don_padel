from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PlaytomicCourtDaySnapshot(Base):
    __tablename__ = "playtomic_court_day_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "venue_id",
            "playtomic_resource_id",
            "day",
            name="uq_playtomic_court_day_snapshots_venue_resource_day",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"), index=True)
    playtomic_resource_id: Mapped[str] = mapped_column(String(128), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    court_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    slots_json: Mapped[list[dict]] = mapped_column(JSONB)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    venue = relationship("Venue", back_populates="playtomic_court_day_snapshots")
