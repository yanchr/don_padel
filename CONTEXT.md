# don_padel Context

## Purpose

Build a Switzerland-focused availability monitor for Playtomic-listed padel venues.

The app stores periodic snapshots so users can inspect current and historical booking pressure.

## Product scope (MVP)

- Playtomic-only venue coverage for Switzerland.
- Read-only monitoring (no booking actions).
- Views:
  - venue list with free/booked summary,
  - Switzerland map markers,
  - time-based lookup for past snapshots.

## Technical architecture

- **Frontend:** React + Vite + TypeScript (`frontend/`)
- **Backend:** FastAPI (`backend/app/main.py`)
- **Persistence:** PostgreSQL via SQLAlchemy models and Alembic migration
- **Deployment:** single Railway service via root `Dockerfile`

## Data model snapshot

- `venues`:
  - venue identity, coordinates, city/country, raw metadata
- `availability_snapshots`:
  - per venue/court time slots, status, captured timestamp
- `ingestion_runs`:
  - execution bookkeeping (status, counts, errors)

## Ingestion behavior

- Runs on interval (`INGEST_INTERVAL_MINUTES`) through APScheduler.
- Can be triggered manually with `POST /api/internal/ingest`.
- Uses `SWISS_SEED_SLUGS` (comma-separated Playtomic club slugs) as discovery seed.
- For each seed slug:
  - fetches club page,
  - parses Next.js bootstrap payload (`__NEXT_DATA__`),
  - stores venue metadata and resource-level availability signal rows.

## Discovery spike findings (2026-04-16)

- Public page [`https://playtomic.com/padel-courts`](https://playtomic.com/padel-courts) is mostly marketing and links into app flow.
- Club pages (example [`https://playtomic.com/clubs/pdl-zurich`](https://playtomic.com/clubs/pdl-zurich)) are Next.js rendered and include a `__NEXT_DATA__` payload with:
  - `tenant` metadata,
  - venue resources,
  - UI messages for availability states.
- In static bundle inspection, direct stable availability endpoint strings were not reliably exposed, so the MVP parser currently uses the page payload and keeps parser/collector logic isolated in `backend/app/services/playtomic_client.py`.
- This keeps the implementation ready for a future switch to explicit JSON endpoint calls once endpoint contract is validated in browser network traces.

## Risks and caveats

- Scraping/web-derived integration can break without notice.
- Terms of use must be reviewed before production operation.
- Current seed-slug strategy is not guaranteed to enumerate every Swiss venue; add broader discovery logic over time.

## Next evolution paths

1. Expand venue discovery to robust Switzerland enumeration.
2. Replace coarse slot signal with true slot-level availability feed once endpoint schema is confirmed.
3. Add data quality monitoring and retry/backoff strategy.
4. Add retention policies and partitioning for long history at scale.
