from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import AvailabilitySnapshot, IngestionRun, Venue
from app.services.playtomic_client import PlaytomicClient


def run_ingestion(db: Session, settings: Settings) -> IngestionRun:
    started_at = datetime.now(UTC)
    run = IngestionRun(
        started_at=started_at,
        status="running",
        venues_seen=0,
        snapshots_written=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    client = PlaytomicClient(settings)
    try:
        venues = client.discover_swiss_venues()
        run.venues_seen = len(venues)

        for discovered in venues:
            existing = db.execute(
                select(Venue).where(Venue.playtomic_venue_id == discovered.playtomic_venue_id)
            ).scalar_one_or_none()

            if existing is None:
                existing = Venue(
                    playtomic_venue_id=discovered.playtomic_venue_id,
                    slug=discovered.slug,
                    name=discovered.name,
                    city=discovered.city,
                    country=discovered.country,
                    latitude=discovered.latitude,
                    longitude=discovered.longitude,
                    raw_metadata=discovered.raw_metadata,
                )
                db.add(existing)
                db.flush()
            else:
                existing.slug = discovered.slug
                existing.name = discovered.name
                existing.city = discovered.city
                existing.country = discovered.country
                existing.latitude = discovered.latitude
                existing.longitude = discovered.longitude
                existing.raw_metadata = discovered.raw_metadata
                db.flush()

            slots = client.discover_availability(discovered)
            captured_at = datetime.now(UTC)
            # Idempotency: one snapshot set per venue + timestamp window.
            db.execute(
                delete(AvailabilitySnapshot).where(
                    AvailabilitySnapshot.venue_id == existing.id,
                    AvailabilitySnapshot.captured_at >= started_at,
                )
            )
            for slot in slots:
                snapshot = AvailabilitySnapshot(
                    venue_id=existing.id,
                    court_label=slot.court_label,
                    slot_start=slot.slot_start,
                    slot_end=slot.slot_end,
                    status=slot.status,
                    available_spots=slot.available_spots,
                    captured_at=captured_at,
                    source_payload=slot.source_payload,
                )
                db.add(snapshot)
                run.snapshots_written += 1
            db.flush()

        run.status = "success"
        run.finished_at = datetime.now(UTC)
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:  # noqa: BLE001
        run.status = "failed"
        run.error = str(exc)
        run.finished_at = datetime.now(UTC)
        db.commit()
        db.refresh(run)
        raise
    finally:
        client.close()
