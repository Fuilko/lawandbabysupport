"""Centralised settings — read once at import, fail fast if misconfigured."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "local"
    database_url: str = "postgresql+asyncpg://legalshield:legalshield@postgres:5432/legalshield"
    cors_origins_raw: str = Field(
        default="http://localhost:8092,http://127.0.0.1:8092",
        validation_alias="CORS_ORIGINS",
    )
    site_base_url: str = "https://legalshield.jp"

    # Privacy: random radial offset applied to incident-report public geom.
    incident_obfuscate_min_m: int = 100
    incident_obfuscate_max_m: int = 300

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
