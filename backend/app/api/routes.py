from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import Select, case, desc, func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db
from app.models import AvailabilitySnapshot, IngestionRun, Venue
from app.schemas.venue import AvailabilitySlotOut, VenueAvailabilityOut, VenueOut, VenueSummary
from app.services.ingestion import run_ingestion
from app.services.playtomic_daily_ingestion import run_playtomic_daily_availability_ingestion

router = APIRouter(prefix="/api")


def _summaries_for_venues(
    db: Session, venue_ids: list[int], at: datetime
) -> dict[int, VenueSummary]:
    if not venue_ids:
        return {}
    rows = db.execute(
        select(
            AvailabilitySnapshot.venue_id,
            func.count(AvailabilitySnapshot.id),
            func.sum(case((AvailabilitySnapshot.status == "free", 1), else_=0)),
            func.sum(case((AvailabilitySnapshot.status == "booked", 1), else_=0)),
        ).where(
            AvailabilitySnapshot.venue_id.in_(venue_ids),  # noqa: PGH003
            AvailabilitySnapshot.captured_at <= at,
        ).group_by(AvailabilitySnapshot.venue_id)
    ).all()

    by_venue: dict[int, VenueSummary] = {}
    for venue_id, total_slots, free_slots, booked_slots in rows:
        by_venue[venue_id] = VenueSummary(
            total_slots=total_slots or 0,
            free_slots=free_slots or 0,
            booked_slots=booked_slots or 0,
        )
    return by_venue


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/venues", response_model=list[VenueOut])
def list_venues(
    at: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[VenueOut]:
    selected_at = at.astimezone(UTC) if at else datetime.now(UTC)
    venues = db.execute(select(Venue).where(Venue.country == "CH").order_by(Venue.name.asc())).scalars().all()
    summaries = _summaries_for_venues(db, [venue.id for venue in venues], selected_at)
    return [
        VenueOut(
            id=venue.id,
            playtomic_venue_id=venue.playtomic_venue_id,
            slug=venue.slug,
            name=venue.name,
            city=venue.city,
            country=venue.country,
            latitude=venue.latitude,
            longitude=venue.longitude,
            summary=summaries.get(venue.id, VenueSummary()),
        )
        for venue in venues
    ]


@router.get("/map", response_model=list[VenueOut])
def map_data(
    at: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[VenueOut]:
    return list_venues(at=at, db=db)


@router.get("/venues/{venue_id}/availability", response_model=VenueAvailabilityOut)
def venue_availability(
    venue_id: int,
    at: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
) -> VenueAvailabilityOut:
    selected_at = at.astimezone(UTC) if at else datetime.now(UTC)
    venue = db.execute(select(Venue).where(Venue.id == venue_id)).scalar_one_or_none()
    if venue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found.")

    latest_capture_stmt: Select[tuple[datetime | None]] = (
        select(func.max(AvailabilitySnapshot.captured_at))
        .where(AvailabilitySnapshot.venue_id == venue_id, AvailabilitySnapshot.captured_at <= selected_at)
    )
    latest_capture = db.execute(latest_capture_stmt).scalar_one_or_none()
    if latest_capture is None:
        return VenueAvailabilityOut(venue_id=venue_id, at=selected_at, slots=[])

    slots = (
        db.execute(
            select(AvailabilitySnapshot)
            .where(
                AvailabilitySnapshot.venue_id == venue_id,
                AvailabilitySnapshot.captured_at == latest_capture,
            )
            .order_by(AvailabilitySnapshot.slot_start.asc(), AvailabilitySnapshot.court_label.asc())
        )
        .scalars()
        .all()
    )
    return VenueAvailabilityOut(
        venue_id=venue_id,
        at=selected_at,
        slots=[
            AvailabilitySlotOut(
                id=slot.id,
                court_label=slot.court_label,
                slot_start=slot.slot_start,
                slot_end=slot.slot_end,
                status=slot.status,
                available_spots=slot.available_spots,
                captured_at=slot.captured_at,
            )
            for slot in slots
        ],
    )


@router.get("/ingestion/runs")
def ingestion_runs(db: Session = Depends(get_db)) -> list[dict]:
    runs = db.execute(select(IngestionRun).order_by(desc(IngestionRun.started_at)).limit(20)).scalars().all()
    return [
        {
            "id": run.id,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "status": run.status,
            "venues_seen": run.venues_seen,
            "snapshots_written": run.snapshots_written,
            "error": run.error,
        }
        for run in runs
    ]


@router.post("/internal/ingest")
def trigger_ingest(
    x_ingest_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    if x_ingest_secret != settings.ingest_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid ingest secret.")
    run = run_ingestion(db=db, settings=settings)
    return {
        "id": run.id,
        "status": run.status,
        "venues_seen": run.venues_seen,
        "snapshots_written": run.snapshots_written,
    }


@router.post("/internal/ingest-playtomic-availability")
def trigger_playtomic_daily_ingest(
    x_ingest_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    if x_ingest_secret != settings.ingest_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid ingest secret.")
    run = run_playtomic_daily_availability_ingestion(db=db, settings=settings)
    return {
        "id": run.id,
        "status": run.status,
        "venues_seen": run.venues_seen,
        "snapshots_written": run.snapshots_written,
    }
