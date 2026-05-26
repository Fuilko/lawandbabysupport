"""GET /api/v1/legalshield/region-stats/{prefecture_code}

Prefecture-level dashboard: crime rate, support-resource density, population.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

router = APIRouter()


@router.get(
    "/region-stats/{prefecture_code}",
    summary="Prefecture-level statistics panel",
)
async def region_stats(
    prefecture_code: str = Path(..., min_length=2, max_length=2,
                                pattern=r"^[0-9]{2}$",
                                description="JIS X 0401 都道府県コード (例: 13=東京)"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    pref_sql = text(
        """
        SELECT prefecture_code, name_ja, name_en, population, area_km2
        FROM legalshield.prefecture
        WHERE prefecture_code = :pc
        """
    )
    pref = (await session.execute(pref_sql, {"pc": prefecture_code})).mappings().first()
    if not pref:
        raise HTTPException(404, f"Unknown prefecture_code: {prefecture_code}")

    crime_sql = text(
        """
        SELECT COALESCE(SUM(total_count), 0) AS total_12m
        FROM legalshield.crime_grid
        WHERE prefecture_code = :pc
          AND year_month >= TO_CHAR(NOW() - INTERVAL '12 months', 'YYYY-MM')
        """
    )
    crime_total = (await session.execute(crime_sql, {"pc": prefecture_code})).scalar_one()

    org_sql = text(
        """
        SELECT org_type, COUNT(*) AS n
        FROM legalshield.support_org
        WHERE prefecture_code = :pc
        GROUP BY org_type
        """
    )
    org_rows = (await session.execute(org_sql, {"pc": prefecture_code})).mappings().all()
    org_counts = {r["org_type"]: int(r["n"]) for r in org_rows}

    pop = int(pref["population"]) if pref["population"] else None
    crime_per_100k = (
        (crime_total / pop * 100_000) if pop and pop > 0 else None
    )
    org_total = sum(org_counts.values())
    org_per_100k = (
        (org_total / pop * 100_000) if pop and pop > 0 else None
    )

    return {
        "prefecture_code": pref["prefecture_code"],
        "name_ja": pref["name_ja"],
        "name_en": pref["name_en"],
        "population": pop,
        "area_km2": pref["area_km2"],
        "crime_12m_total": int(crime_total),
        "crime_per_100k_pop": crime_per_100k,
        "support_orgs": org_counts,
        "support_orgs_total": org_total,
        "support_orgs_per_100k_pop": org_per_100k,
    }
