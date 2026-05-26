"""GET /api/v1/legalshield/nearest-support

Top-N closest support resources (法テラス / NPO / NGO / 弁護士会) within radius.
Uses PostGIS ST_DWithin (geography) for accurate spherical distance.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

router = APIRouter()

OrgType = Literal["law_terrace", "npo", "ngo", "bar_association"]


@router.get("/nearest-support", summary="Top-N closest support resources")
async def nearest_support(
    lat: float = Query(..., ge=-90, le=90, description="緯度 WGS84"),
    lng: float = Query(..., ge=-180, le=180, description="経度 WGS84"),
    radius_km: float = Query(5.0, gt=0, le=200, description="検索半径 (km)"),
    type: Optional[OrgType] = Query(None, description="絞り込み用 org_type"),
    service: Optional[str] = Query(None, description="提供サービス絞り込み (例: domestic_violence)"),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> dict:
    point_wkt = f"POINT({lng} {lat})"
    radius_m = radius_km * 1000.0

    sql = text(
        """
        SELECT
          id,
          org_type,
          name,
          prefecture_code,
          address,
          services,
          contact,
          source,
          source_url,
          ST_Distance(geom, ST_GeogFromText(:pt))                AS distance_m,
          ST_Y(geom::geometry)                                   AS lat,
          ST_X(geom::geometry)                                   AS lng
        FROM legalshield.support_org
        WHERE geom IS NOT NULL
          AND ST_DWithin(geom, ST_GeogFromText(:pt), :radius_m)
          AND (CAST(:org_type AS text) IS NULL OR org_type = :org_type)
          AND (CAST(:service  AS text) IS NULL OR :service = ANY(services))
        ORDER BY geom <-> ST_GeogFromText(:pt)
        LIMIT :lim
        """
    )

    rows = (
        await session.execute(
            sql,
            {
                "pt": point_wkt,
                "radius_m": radius_m,
                "org_type": type,
                "service": service,
                "lim": limit,
            },
        )
    ).mappings().all()

    return {
        "query": {"lat": lat, "lng": lng, "radius_km": radius_km, "type": type, "service": service},
        "count": len(rows),
        "results": [dict(r) for r in rows],
    }
