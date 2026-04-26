from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.config import get_settings
from app.db.session import SessionLocal
from app.services.ingestion import run_ingestion
from app.services.playtomic_daily_ingestion import run_playtomic_daily_availability_ingestion

settings = get_settings()
scheduler = BackgroundScheduler()


def _run_scheduled_ingest() -> None:
    db = SessionLocal()
    try:
        run_ingestion(db=db, settings=settings)
    finally:
        db.close()


def _run_scheduled_playtomic_daily_ingest() -> None:
    db = SessionLocal()
    try:
        run_playtomic_daily_availability_ingestion(db=db, settings=settings)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.ingest_interval_minutes > 0 and not scheduler.running:
        scheduler.add_job(
            _run_scheduled_ingest,
            trigger="interval",
            minutes=settings.ingest_interval_minutes,
            id="periodic-ingest",
            replace_existing=True,
        )
    if settings.playtomic_daily_cron_enabled:
        scheduler.add_job(
            _run_scheduled_playtomic_daily_ingest,
            trigger="cron",
            hour=settings.playtomic_daily_cron_hour,
            minute=settings.playtomic_daily_cron_minute,
            timezone=settings.playtomic_availability_timezone,
            id="playtomic-daily-ingest",
            replace_existing=True,
        )
    if not scheduler.running and scheduler.get_jobs():
        scheduler.start()
    try:
        yield
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)


app = FastAPI(title="don_padel API", lifespan=lifespan)
app.include_router(api_router)

frontend_dist = (Path(__file__).resolve().parent.parent / settings.frontend_dist_path).resolve()
if frontend_dist.exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):  # noqa: ARG001
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Frontend build not found. Build frontend first."}
