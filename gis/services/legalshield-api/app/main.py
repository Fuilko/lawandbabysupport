"""LegalShield-jp FastAPI entry point.

Operational notes (lessons learned from hiiforest 2026-05-24 outage):

1. Every optional endpoint module is wrapped in try/except so a single broken
   import does not take down the whole service.
2. /health is dead-simple (no DB call) so docker-compose / GH Actions can
   distinguish "container is up" from "DB is reachable" (use /health/db
   for the latter).
3. CORS origins come from env CORS_ORIGINS (comma-separated). Never use
   allow_origins=['*'] together with allow_credentials=True (browsers reject).
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.db import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("legalshield")

settings = get_settings()

app = FastAPI(
    title="LegalShield-jp API",
    description="Japan legal-aid GIS platform — nearest support + risk indicators.",
    version="0.1.0",
)

# Compression for GeoJSON / vector-tile payloads.
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["http://localhost:8092"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
logger.info("CORS allowed origins: %s", settings.cors_origins)

# (GZipMiddleware is already added above; do NOT add it twice.)

# ─── Defensive endpoint imports ─────────────────────────────────────
# Each router is loaded with try/except so one failing module does not
# take down the whole service. Mirrors the hiiforest pattern.

ROUTER_MODULES = (
    "nearest_support",
    "risk_score",
    "incident_report",
    "region_stats",
    "tiles",
    "categories",
    "intake",
)

_router_status: Dict[str, str] = {}

for _name in ROUTER_MODULES:
    try:
        _mod = __import__(f"app.api.{_name}", fromlist=["router"])
        app.include_router(_mod.router, prefix="/api/v1/legalshield", tags=[_name])
        _router_status[_name] = "loaded"
        logger.info("Router loaded: %s", _name)
    except Exception as exc:  # noqa: BLE001 — defensive
        _router_status[_name] = f"failed: {exc!r}"
        logger.exception("Router %s failed to load — continuing without it", _name)


# ─── Liveness / readiness ───────────────────────────────────────────

@app.get("/health", tags=["meta"])
async def health() -> Dict[str, Any]:
    """Liveness probe. Does NOT touch the DB so containers stay healthy
    even during transient DB hiccups (which are surfaced via /health/db)."""
    return {
        "status": "ok",
        "service": "legalshield-api",
        "env": settings.app_env,
        "routers": _router_status,
    }


@app.get("/health/db", tags=["meta"])
async def health_db() -> JSONResponse:
    """Readiness probe: SELECT 1 against the DB."""
    try:
        async with engine.connect() as conn:
            row = (await conn.execute(text("SELECT 1"))).scalar_one()
        return JSONResponse({"status": "ok", "db": int(row)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("DB health check failed")
        return JSONResponse(
            {"status": "error", "detail": repr(exc)},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@app.get("/", tags=["meta"])
async def root() -> Dict[str, Any]:
    return {
        "service": "LegalShield-jp",
        "docs": "/docs",
        "health": "/health",
        "version": app.version,
    }
