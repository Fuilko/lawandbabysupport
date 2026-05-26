"""POST /api/v1/legalshield/incident-report

Anonymous user incident submission.

Privacy:
* Real coordinates (`geom`) are stored server-side but NEVER returned via API.
* `obfuscated_geom` is a polygon of radius R metres around a randomly offset
  centre point, where R is uniformly drawn from [INCIDENT_OBFUSCATE_MIN_M,
  INCIDENT_OBFUSCATE_MAX_M] env vars (defaults 100-300 m).
* A SHA-256 hash of (client_ip + UA + daily_salt) is stored as `client_hash`
  for rate limiting only — the raw inputs are never persisted.
"""
from __future__ import annotations

import hashlib
import math
import random
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session

router = APIRouter()
settings = get_settings()


class IncidentReportIn(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    incident_type: str = Field(..., max_length=64,
                                description="例: harassment, dv, stalking, fraud, other")
    description: Optional[str] = Field(None, max_length=2000)
    anonymous: bool = Field(True, description="Must be true for now (privacy default).")


@router.post(
    "/incident-report",
    status_code=201,
    summary="Submit anonymous incident report (geom obfuscated 100-300m)",
)
async def submit_incident(
    payload: IncidentReportIn,
    request: Request,
    user_agent: str = Header("", alias="User-Agent"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if not payload.anonymous:
        raise HTTPException(400, "Only anonymous reports are accepted in this version.")

    obfuscated_polygon_wkt = _obfuscate_polygon(
        payload.lat,
        payload.lng,
        settings.incident_obfuscate_min_m,
        settings.incident_obfuscate_max_m,
    )

    client_hash = _client_hash(request.client.host if request.client else "unknown", user_agent)

    sql = text(
        """
        INSERT INTO legalshield.incident_report
          (geom, obfuscated_geom, incident_type, description, client_hash)
        VALUES
          (ST_GeogFromText(:geom),
           ST_GeogFromText(:obf),
           :itype,
           :desc,
           :ch)
        RETURNING id, reported_at
        """
    )
    row = (
        await session.execute(
            sql,
            {
                "geom": f"POINT({payload.lng} {payload.lat})",
                "obf": obfuscated_polygon_wkt,
                "itype": payload.incident_type,
                "desc": payload.description,
                "ch": client_hash,
            },
        )
    ).mappings().one()
    await session.commit()

    return {
        "status": "accepted",
        "id": str(row["id"]),
        "reported_at": row["reported_at"].isoformat(),
        "obfuscation_radius_m": [
            settings.incident_obfuscate_min_m,
            settings.incident_obfuscate_max_m,
        ],
    }


# ─── helpers ────────────────────────────────────────────────────────

_EARTH_R = 6_378_137.0


def _offset_latlng(lat: float, lng: float, dx_m: float, dy_m: float) -> tuple[float, float]:
    """Approximate metric → degree offset (good enough for <1 km offsets)."""
    dlat = (dy_m / _EARTH_R) * (180.0 / math.pi)
    dlng = (dx_m / (_EARTH_R * math.cos(math.radians(lat)))) * (180.0 / math.pi)
    return lat + dlat, lng + dlng


def _obfuscate_polygon(lat: float, lng: float, min_m: int, max_m: int, sides: int = 16) -> str:
    """Return a WKT polygon centred at a randomly offset point with random radius."""
    # 1. random offset of the centre
    theta_off = random.random() * 2 * math.pi
    r_off = random.uniform(min_m, max_m)
    cx_lat, cx_lng = _offset_latlng(lat, lng,
                                     r_off * math.cos(theta_off),
                                     r_off * math.sin(theta_off))
    # 2. polygon radius = random in [min_m, max_m]
    r_poly = random.uniform(min_m, max_m)
    pts = []
    for k in range(sides):
        a = 2 * math.pi * k / sides
        plat, plng = _offset_latlng(cx_lat, cx_lng,
                                     r_poly * math.cos(a),
                                     r_poly * math.sin(a))
        pts.append(f"{plng} {plat}")
    pts.append(pts[0])  # close ring
    return f"POLYGON(({','.join(pts)}))"


def _client_hash(ip: str, ua: str) -> str:
    """Daily-rotating salted hash for rate limiting. Raw inputs never stored."""
    salt = date.today().isoformat()
    h = hashlib.sha256(f"{ip}|{ua}|{salt}".encode("utf-8")).hexdigest()
    return h[:32]
