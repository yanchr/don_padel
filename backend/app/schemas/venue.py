from datetime import datetime

from pydantic import BaseModel, Field


class VenueSummary(BaseModel):
    total_slots: int = 0
    free_slots: int = 0
    booked_slots: int = 0


class VenueOut(BaseModel):
    id: int
    playtomic_venue_id: str
    slug: str | None = None
    name: str
    city: str | None = None
    country: str
    latitude: float | None = None
    longitude: float | None = None
    summary: VenueSummary


class AvailabilitySlotOut(BaseModel):
    id: int
    court_label: str
    slot_start: datetime
    slot_end: datetime
    status: str
    available_spots: int | None = None
    captured_at: datetime


class VenueAvailabilityOut(BaseModel):
    venue_id: int
    at: datetime = Field(description="Point in time used to resolve snapshots.")
    slots: list[AvailabilitySlotOut]
