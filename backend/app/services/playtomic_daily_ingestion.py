from __future__ import annotations

import time
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import IngestionRun, PlaytomicCourtDaySnapshot, Venue


def _target_days(settings: Settings) -> list[date]:
    tz = ZoneInfo(settings.playtomic_availability_timezone)
    today = datetime.now(tz).date()
    return [today + timedelta(days=offset) for offset in range(settings.playtomic_availability_days)]


def _as_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _extract_tenant_location(payload: dict) -> tuple[float | None, float | None]:
    point = payload.get("point") if isinstance(payload.get("point"), dict) else {}
    latitude = _as_float(point.get("lat")) or _as_float(payload.get("latitude")) or _as_float(payload.get("lat"))
    longitude = _as_float(point.get("lon")) or _as_float(payload.get("longitude")) or _as_float(payload.get("lon"))
    return latitude, longitude


def _load_tenant_payload(client: httpx.Client, tenant_id: str) -> dict:
    response = client.get(f"/v1/tenants/{tenant_id}")
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        return {}
    return payload


def _load_resource_names(payload: dict) -> dict[str, str]:
    resources = payload.get("resources") if isinstance(payload, dict) else []
    names: dict[str, str] = {}
    if not isinstance(resources, list):
        return names
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        resource_id = resource.get("resource_id")
        resource_name = resource.get("name")
        if isinstance(resource_id, str) and isinstance(resource_name, str):
            names[resource_id] = resource_name
    return names


def run_playtomic_daily_availability_ingestion(db: Session, settings: Settings) -> IngestionRun:
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

    web_client = httpx.Client(
        base_url=settings.playtomic_base_url,
        timeout=settings.ingest_timeout_seconds,
        headers={"User-Agent": settings.ingest_user_agent},
        follow_redirects=True,
    )
    api_client = httpx.Client(
        base_url=settings.playtomic_api_base_url,
        timeout=settings.ingest_timeout_seconds,
        headers={"User-Agent": settings.ingest_user_agent},
        follow_redirects=True,
    )
    try:
        venues = (
            db.execute(
                select(Venue)
                .where(Venue.country == "CH")
                .order_by(Venue.name.asc())
            )
            .scalars()
            .all()
        )
        run.venues_seen = len(venues)
        target_days = _target_days(settings)

        for venue in venues:
            tenant_id = venue.playtomic_venue_id
            if not tenant_id:
                continue

            try:
                tenant_payload = _load_tenant_payload(api_client, tenant_id)
                resource_names = _load_resource_names(tenant_payload)
                latitude, longitude = _extract_tenant_location(tenant_payload)
                if latitude is not None and longitude is not None:
                    venue.latitude = latitude
                    venue.longitude = longitude
                    db.flush()
            except httpx.HTTPError:
                resource_names = {}

            for target_day in target_days:
                response = web_client.get(
                    "/api/clubs/availability",
                    params={
                        "tenant_id": tenant_id,
                        "date": target_day.isoformat(),
                        "sport_id": settings.playtomic_daily_sport_id,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, list):
                    continue

                captured_at = datetime.now(UTC)
                for resource in payload:
                    if not isinstance(resource, dict):
                        continue
                    resource_id = resource.get("resource_id")
                    if not isinstance(resource_id, str):
                        continue
                    slots = resource.get("slots")
                    if not isinstance(slots, list):
                        slots = []

                    start_date_raw = resource.get("start_date")
                    day_value = target_day
                    if isinstance(start_date_raw, str):
                        try:
                            day_value = date.fromisoformat(start_date_raw)
                        except ValueError:
                            day_value = target_day

                    stmt = insert(PlaytomicCourtDaySnapshot).values(
                        venue_id=venue.id,
                        playtomic_resource_id=resource_id,
                        day=day_value,
                        court_name=resource_names.get(resource_id),
                        slots_json=slots,
                        captured_at=captured_at,
                    )
                    stmt = stmt.on_conflict_do_update(
                        constraint="uq_playtomic_court_day_snapshots_venue_resource_day",
                        set_={
                            "court_name": resource_names.get(resource_id),
                            "slots_json": slots,
                            "captured_at": captured_at,
                        },
                    )
                    db.execute(stmt)
                    run.snapshots_written += 1
                db.flush()
                time.sleep(max(settings.ingest_delay_ms, 0) / 1000)

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
        web_client.close()
        api_client.close()
