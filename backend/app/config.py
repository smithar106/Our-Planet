"""Application configuration.

All settings are read from environment variables (or a local .env file).
Secrets must never be committed or exposed to the client.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Runtime ---------------------------------------------------------
    app_name: str = "PLANET"
    environment: str = "development"  # development | production
    log_level: str = "INFO"

    # --- Database --------------------------------------------------------
    database_url: str = Field(
        default="postgresql+asyncpg://planet:planet@localhost:5432/planet",
        alias="DATABASE_URL",
    )

    # --- Data sources ----------------------------------------------------
    usgs_feed_url: str = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
    eonet_api_url: str = "https://eonet.gsfc.nasa.gov/api/v3/events"
    firms_api_url: str = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
    nasa_firms_map_key: str | None = Field(default=None, alias="NASA_FIRMS_MAP_KEY")

    # --- LLM -------------------------------------------------------------
    llm_provider: str = Field(default="deepseek", alias="LLM_PROVIDER")
    llm_model: str = Field(default="deepseek-chat", alias="LLM_MODEL")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_base_url: str | None = Field(default=None, alias="LLM_BASE_URL")
    llm_timeout_seconds: float = 60.0

    # --- Agent -----------------------------------------------------------
    agent_threshold: float = Field(default=50.0, alias="AGENT_THRESHOLD")  # significance score to trigger investigation

    # --- Pipeline cadence (seconds) --------------------------------------
    usgs_interval_seconds: int = 300  # 5 minutes
    eonet_interval_seconds: int = 900  # 15 minutes
    firms_interval_seconds: int = 1800  # 30 minutes
    brief_interval_seconds: int = 86400  # 24 hours

    # --- FIRMS clustering ------------------------------------------------
    fire_cluster_radius_km: float = 5.0

    # --- HTTP ------------------------------------------------------------
    http_timeout_seconds: float = 30.0
    http_max_retries: int = 3

    # --- Observability ---------------------------------------------------
    tracing_backend: str = "memory"  # memory | mlflow | null
    mlflow_tracking_uri: str | None = Field(default=None, alias="MLFLOW_TRACKING_URI")

    # --- Misc ------------------------------------------------------------
    cors_origins: str = "*"
    timezone: str = "UTC"

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
