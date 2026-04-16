from functools import lru_cache

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
