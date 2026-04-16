from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from dateutil import parser as date_parser

from app.config import Settings

NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.DOTALL
)


@dataclass
class DiscoveredVenue:
    playtomic_venue_id: str
    slug: str
    name: str
    city: str | None
    country: str
    latitude: float | None
    longitude: float | None
    raw_metadata: dict


@dataclass
class DiscoveredSlot:
    court_label: str
    slot_start: datetime
    slot_end: datetime
    status: str
    available_spots: int | None
    source_payload: dict


class PlaytomicClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.Client(
            base_url=settings.playtomic_base_url,
            timeout=settings.ingest_timeout_seconds,
            headers={"User-Agent": settings.ingest_user_agent},
            follow_redirects=True,
        )

    def close(self) -> None:
        self.client.close()

    def _extract_next_data(self, html: str) -> dict:
        match = NEXT_DATA_RE.search(html)
        if not match:
            raise ValueError("Could not find __NEXT_DATA__ script payload.")
        return json.loads(match.group(1))

    def _slug_candidates(self) -> list[str]:
        return [slug.strip() for slug in self.settings.swiss_seed_slugs.split(",") if slug.strip()]

    def discover_swiss_venues(self) -> list[DiscoveredVenue]:
        venues: list[DiscoveredVenue] = []
        for slug in self._slug_candidates():
            path = f"/clubs/{slug}"
            response = self.client.get(path)
            response.raise_for_status()
            page_data = self._extract_next_data(response.text)
            tenant = page_data.get("props", {}).get("pageProps", {}).get("tenant", {})
            venue_id = str(tenant.get("tenant_id") or slug)
            city = tenant.get("address", {}).get("city") if isinstance(tenant.get("address"), dict) else None
            country = (
                tenant.get("address", {}).get("country_code")
                if isinstance(tenant.get("address"), dict)
                else None
            )
            # Best-effort fallback to CH because this collector is Switzerland-scoped.
            country = (country or "CH").upper()
            point = tenant.get("point") if isinstance(tenant.get("point"), dict) else {}
            latitude = point.get("lat")
            longitude = point.get("lon")
            venue = DiscoveredVenue(
                playtomic_venue_id=venue_id,
                slug=tenant.get("slug") or slug,
                name=tenant.get("tenant_name") or slug.replace("-", " ").title(),
                city=city,
                country=country,
                latitude=latitude,
                longitude=longitude,
                raw_metadata=tenant,
            )
            if venue.country == "CH":
                venues.append(venue)
            time.sleep(max(self.settings.ingest_delay_ms, 0) / 1000)
        return venues

    def discover_availability(self, venue: DiscoveredVenue) -> list[DiscoveredSlot]:
        # Club pages expose availability status in the rendered content but not full slot JSON.
        # For MVP we snapshot current signal from the page and persist it time-series style.
        response = self.client.get(f"/clubs/{venue.slug}")
        response.raise_for_status()
        page_data = self._extract_next_data(response.text)
        tenant = page_data.get("props", {}).get("pageProps", {}).get("tenant", {})
        resources = tenant.get("resources") if isinstance(tenant, dict) else []
        now = datetime.now(UTC)
        slot_end = now + timedelta(hours=self.settings.ingest_default_window_hours)

        slots: list[DiscoveredSlot] = []
        for resource in resources or []:
            label = resource.get("name") or "Court"
            slots.append(
                DiscoveredSlot(
                    court_label=label,
                    slot_start=now,
                    slot_end=slot_end,
                    status="unknown",
                    available_spots=None,
                    source_payload=resource,
                )
            )

        if not slots:
            # If no resources are included in page props, keep one aggregate row.
            slots.append(
                DiscoveredSlot(
                    court_label="All courts",
                    slot_start=now,
                    slot_end=slot_end,
                    status="unknown",
                    available_spots=None,
                    source_payload={"note": "No resource-level data found in page payload."},
                )
            )

        # Preserve first-party availability hints when present in page props.
        availability_date = page_data.get("query", {}).get("date")
        if availability_date:
            try:
                parsed = date_parser.isoparse(availability_date)
                for slot in slots:
                    slot.slot_start = parsed.astimezone(UTC)
                    slot.slot_end = slot.slot_start + timedelta(hours=self.settings.ingest_default_window_hours)
            except ValueError:
                pass

        time.sleep(max(self.settings.ingest_delay_ms, 0) / 1000)
        return slots
