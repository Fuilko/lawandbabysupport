"""GET /api/v1/legalshield/risk-score

Returns the past-12-month crime density at the user's location and its
nation-wide percentile rank, based on the 500-m crime grid.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

router = APIRouter()


@router.get("/risk-score", summary="Local 12-month crime density + percentile")
async def risk_score(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    session: AsyncSession = Depends(get_session),
) -> dict:
    point_wkt = f"POINT({lng} {lat})"

    grid_sql = text(
        """
        SELECT grid_id,
               prefecture_code,
               total_12m
        FROM legalshield.crime_grid_12m
        WHERE ST_Intersects(geom, ST_GeogFromText(:pt))
        LIMIT 1
        """
    )
    grid_row = (await session.execute(grid_sql, {"pt": point_wkt})).mappings().first()

    if not grid_row:
        raise HTTPException(
            status_code=404,
            detail="No crime grid covers this location. Coverage may be limited "
                   "to populated mesh; check input or wait for ingest.",
        )

    pct_sql = text(
        """
        SELECT
          PERCENT_RANK() OVER (ORDER BY total_12m) AS pr
        FROM legalshield.crime_grid_12m
        WHERE grid_id = :gid
        """
    )
    # Compute percentile for this grid in one shot (window over all rows).
    full_sql = text(
        """
        WITH ranked AS (
          SELECT grid_id,
                 total_12m,
                 PERCENT_RANK() OVER (ORDER BY total_12m) AS pr
          FROM legalshield.crime_grid_12m
        )
        SELECT pr FROM ranked WHERE grid_id = :gid
        """
    )
    pr = (await session.execute(full_sql, {"gid": grid_row["grid_id"]})).scalar_one_or_none()

    return {
        "query": {"lat": lat, "lng": lng},
        "grid_id": grid_row["grid_id"],
        "prefecture_code": grid_row["prefecture_code"],
        "crime_12m_count": int(grid_row["total_12m"] or 0),
        "national_percentile": float(pr) if pr is not None else None,
        "interpretation": _interpret(pr),
    }


def _interpret(pr: float | None) -> str:
    if pr is None:
        return "unknown"
    if pr >= 0.9:
        return "very_high"
    if pr >= 0.75:
        return "high"
    if pr >= 0.4:
        return "moderate"
    if pr >= 0.1:
        return "low"
    return "very_low"
