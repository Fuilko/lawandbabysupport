"""Shared helpers for ingest pipelines.

All ingest jobs follow the same shape:
  start_run("dataset")  ->  fetch + transform  ->  finish_run("success", n_in, n_out)

DB writes are idempotent — UPSERT on (source, source_id) for support_org,
PRIMARY KEY for prefecture/city, (grid_id, year_month) for crime_grid.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger("legalshield.ingest")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://legalshield:legalshield@postgres:5432/legalshield",
)
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/app/data"))
RAW_DIR = DATA_ROOT / "raw"
PROCESSED_DIR = DATA_ROOT / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
SessionFactory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as s:
        try:
            yield s
            await s.commit()
        except Exception:
            await s.rollback()
            raise


async def start_run(session: AsyncSession, dataset: str) -> int:
    row = (
        await session.execute(
            text(
                "INSERT INTO legalshield.ingest_run (dataset) VALUES (:d) RETURNING id"
            ),
            {"d": dataset},
        )
    ).scalar_one()
    await session.commit()
    return int(row)


async def finish_run(
    session: AsyncSession,
    run_id: int,
    status: str,
    rows_in: Optional[int] = None,
    rows_out: Optional[int] = None,
    notes: Optional[str] = None,
) -> None:
    await session.execute(
        text(
            """
            UPDATE legalshield.ingest_run
               SET finished_at = NOW(),
                   status      = :s,
                   rows_in     = :ri,
                   rows_out    = :ro,
                   notes       = :n
             WHERE id = :id
            """
        ),
        {"s": status, "ri": rows_in, "ro": rows_out, "n": notes, "id": run_id},
    )
    await session.commit()


def http_client(timeout: float = 60.0) -> httpx.AsyncClient:
    """Default async HTTP client with polite UA — please don't change UA without
    coordinating with the upstream data providers."""
    return httpx.AsyncClient(
        timeout=timeout,
        headers={
            "User-Agent": "LegalShield-jp/0.1 (public-interest GIS; +https://legalshield.jp)",
            "Accept": "*/*",
        },
        follow_redirects=True,
    )


async def download(url: str, dest: Path) -> Path:
    """Download a file to dest if not already cached."""
    if dest.exists() and dest.stat().st_size > 0:
        logger.info("cached: %s", dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("downloading: %s -> %s", url, dest)
    async with http_client(timeout=300.0) as cli:
        async with cli.stream("GET", url) as resp:
            resp.raise_for_status()
            with dest.open("wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                    f.write(chunk)
    return dest
