from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/don_padel"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    ingest_interval_minutes: int = 60
    ingest_default_window_hours: int = 24
    ingest_lookback_minutes: int = 0
    ingest_secret: str = "local-dev-secret"
    ingest_user_agent: str = "don-padel-bot/0.1"
    ingest_timeout_seconds: float = 20.0
    ingest_delay_ms: int = 200
    playtomic_base_url: str = "https://playtomic.com"
    swiss_seed_slugs: str = "pdl-zurich"
    frontend_dist_path: str = "../frontend/dist"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def railway_postgres_uses_psycopg3(cls, v: object) -> object:
        """Railway (and others) set DATABASE_URL as postgresql://..., which defaults to psycopg2."""
        if not isinstance(v, str):
            return v
        if v.startswith("postgres://"):
            return "postgresql+psycopg://" + v.removeprefix("postgres://")
        if v.startswith("postgresql://"):
            return "postgresql+psycopg://" + v.removeprefix("postgresql://")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
