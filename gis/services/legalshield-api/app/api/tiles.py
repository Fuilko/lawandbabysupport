"""GET /api/v1/legalshield/tiles/{z}/{x}/{y}.pbf

Mapbox Vector Tile (MVT) endpoint — combines two layers:
  * boundaries  : prefecture polygons (for outline)
  * crime       : crime_grid_12m polygons coloured by total_12m

Uses PostGIS ST_AsMVT for server-side tile generation.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

router = APIRouter()


@router.get(
    "/tiles/{z}/{x}/{y}.pbf",
    summary="MVT vector tile (boundaries + crime density)",
    response_class=Response,
)
async def tile(
    z: int = Path(..., ge=0, le=22),
    x: int = Path(..., ge=0),
    y: int = Path(..., ge=0),
    session: AsyncSession = Depends(get_session),
) -> Response:
    if x >= (1 << z) or y >= (1 << z):
        raise HTTPException(400, "Tile coordinates out of range for zoom level")

    # ST_TileEnvelope is PostGIS 3.0+. We build two MVT layers and concat them.
    sql = text(
        """
        WITH bbox AS (
          SELECT ST_TileEnvelope(:z, :x, :y) AS env
        ),
        boundaries AS (
          SELECT
            prefecture_code,
            name_ja,
            ST_AsMVTGeom(
              ST_Transform(ST_Force2D(geom::geometry), 3857),
              (SELECT env FROM bbox),
              4096, 256, true
            ) AS geom
          FROM legalshield.prefecture
          WHERE geom && ST_Transform((SELECT env FROM bbox), 4326)::geography
        ),
        crime AS (
          SELECT
            grid_id,
            total_12m,
            ST_AsMVTGeom(
              ST_Transform(ST_Force2D(geom::geometry), 3857),
              (SELECT env FROM bbox),
              4096, 256, true
            ) AS geom
          FROM legalshield.crime_grid_12m
          WHERE geom && ST_Transform((SELECT env FROM bbox), 4326)::geography
            AND :z >= 10                            -- only show grid at z>=10
        )
        SELECT (
          (SELECT ST_AsMVT(boundaries.*, 'boundaries', 4096, 'geom') FROM boundaries WHERE geom IS NOT NULL)
          ||
          (SELECT ST_AsMVT(crime.*, 'crime', 4096, 'geom') FROM crime WHERE geom IS NOT NULL)
        ) AS pbf
        """
    )

    res = (await session.execute(sql, {"z": z, "x": x, "y": y})).scalar_one_or_none()
    if not res:
        # empty tile is valid — return 204 so clients cache the void cheaply
        return Response(content=b"", media_type="application/x-protobuf", status_code=204)

    return Response(
        content=bytes(res),
        media_type="application/x-protobuf",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        },
    )
