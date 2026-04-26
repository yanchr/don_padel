# don_padel

`don_padel` is a Playtomic-focused MVP to monitor padel venue availability in Switzerland and explore booking load over time.

## url
https://donpadel-production.up.railway.app/ 

## Project goals

- Ingest schedule-related availability snapshots on a time interval (hourly by default).
- Store snapshots in PostgreSQL for long-term history.
- Offer a frontend with:
  - list of Swiss venues and free/booked signal,
  - map of venues in Switzerland,
  - time navigation to inspect historical snapshots.

## Stack

- Frontend: React + Vite + TypeScript
- Backend: FastAPI + SQLAlchemy + Alembic
- Database: PostgreSQL
- Deployment target: Railway (single service container)

## Repository layout

- `frontend/` React SPA
- `backend/` FastAPI app, ingestion logic, SQL models, migrations
- `Dockerfile` multi-stage build for Railway
- `CONTEXT.md` project context for future chat handoffs

## Local development

### 1) Frontend

```bash
cd /Users/yanickchristen/projects/don_padel/frontend
npm install
npm run dev
```

### 2) Backend

```bash
cd /Users/yanickchristen/projects/don_padel/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Running ingestion

- Scheduled ingestion runs automatically if `INGEST_INTERVAL_MINUTES > 0`.
- You can also trigger manually:

```bash
curl -X POST "http://localhost:8000/api/internal/ingest" \
  -H "x-ingest-secret: change-me"
```

## API overview

- `GET /api/health`
- `GET /api/venues?at=ISO8601`
- `GET /api/map?at=ISO8601`
- `GET /api/venues/{venue_id}/availability?at=ISO8601`
- `POST /api/internal/ingest` (requires `x-ingest-secret`)
- `GET /api/ingestion/runs`

## Railway deployment

1. Create a Railway project and add PostgreSQL.
2. Deploy this repo using the root `Dockerfile`.
3. Set environment variables from `backend/.env.example` (especially `DATABASE_URL`, `INGEST_SECRET`, `SWISS_SEED_SLUGS`).
4. Run migrations:

```bash
cd /app/backend && alembic -c alembic.ini upgrade head
```

## Data source and legal note

This MVP uses web-derived Playtomic data flow assumptions from public pages such as [Playtomic padel courts](https://playtomic.com/padel-courts) and club pages (for example [Timing club page](https://playtomic.com/clubs/timing)).

Playtomic’s official Club API is designed for partner clubs and is not a general public “all courts” API: [Playtomic API guide](https://helpmanager.playtomic.com/hc/en-gb/articles/38836515997073-Playtomic-API-Complete-Guide).

You should review Playtomic terms and applicable law before production scraping, then add strict rate-limiting and monitoring.
