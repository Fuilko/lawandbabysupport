"""
Q-Map 集計 API
================

iOS / Web の Q-Map (`gis/frontend/qmap_prototype.html`) が呼ぶ集計 endpoint。

- インシデント（VoiceTriageEvent）を H3 hex に集約
- k-匿名性ゲート（k 未満の hex は返さない）
- 仮想都市変換（実座標を高知市庁舎中心に正規化）
- カテゴリ × 緊急度ごとに件数返す

GET /api/aggregate/incidents?res=460&k=5&virtual=true
GET /api/aggregate/supports?prefecture=高知県
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/aggregate", tags=["aggregate"])

# 仮想都市の中心（高知市庁舎）
VIRTUAL_ORIGIN_LAT = 33.5597
VIRTUAL_ORIGIN_LON = 133.5311


# ────────────────────────────────────────────
# 簡易 H3 風 hex index（Swift 側 LocationAnonymizer と整合）
# ────────────────────────────────────────────

def hex_index(lat: float, lon: float, resolution_m: float) -> str:
    meters_per_deg_lat = 111_320.0
    meters_per_deg_lon = 111_320.0 * math.cos(math.radians(lat))
    cell_lat = resolution_m / meters_per_deg_lat
    cell_lon = resolution_m / meters_per_deg_lon
    q = round(lon / cell_lon)
    r = round(lat / cell_lat)
    return f"ls_h{int(resolution_m)}_q{q}_r{r}"


def hex_center(idx: str) -> tuple[float, float] | None:
    try:
        parts = idx.split("_")
        res = float(parts[1].lstrip("h"))
        q = int(parts[2].lstrip("q"))
        r = int(parts[3].lstrip("r"))
    except (ValueError, IndexError):
        return None
    meters_per_deg_lat = 111_320.0
    lat = r * (res / meters_per_deg_lat)
    meters_per_deg_lon = 111_320.0 * math.cos(math.radians(lat))
    lon = q * (res / meters_per_deg_lon)
    return lat, lon


def to_virtual_city(lat: float, lon: float) -> tuple[float, float]:
    """実座標 → 仮想都市座標（中心を高知市庁舎に置く）"""
    return lat, lon  # 既に高知中心の場合は同じ。本番は集計ベース変換ロジック。


# ────────────────────────────────────────────
# データソース（暫定：JSON ファイル、本番は DB）
# ────────────────────────────────────────────

INCIDENTS_FILE = Path(__file__).parent.parent / "data" / "incidents_recent.jsonl"


def _load_incidents() -> list[dict[str, Any]]:
    if not INCIDENTS_FILE.exists():
        return []
    items = []
    for line in INCIDENTS_FILE.open(encoding="utf-8"):
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return items


# ────────────────────────────────────────────
# /api/aggregate/incidents
# ────────────────────────────────────────────

@router.get("/incidents")
def aggregate_incidents(
    res: float = Query(460.0, description="hex 解像度 [m]"),
    k: int = Query(5, ge=1, description="k-匿名性閾値"),
    virtual: bool = Query(True, description="仮想都市変換"),
    category: str | None = Query(None, description="特定カテゴリのみ"),
    since_hours: int = Query(720, description="直近 N 時間（720 = 30日）"),
) -> dict[str, Any]:
    """インシデントを H3 hex に集約して GeoJSON で返す"""
    incidents = _load_incidents()

    # フィルタ
    if category:
        incidents = [i for i in incidents if i.get("triage", {}).get("category") == category]

    # 集約
    bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for inc in incidents:
        loc = inc.get("location")
        if not loc:
            continue
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        if lat is None or lon is None:
            continue
        idx = hex_index(lat, lon, res)
        bucket[idx].append(inc)

    # k-匿名性
    features = []
    for idx, items in bucket.items():
        if len(items) < k:
            continue
        center = hex_center(idx)
        if not center:
            continue
        c_lat, c_lon = center
        if virtual:
            c_lat, c_lon = to_virtual_city(c_lat, c_lon)
        # 最頻カテゴリ・最大緊急度
        cat_counts: dict[str, int] = defaultdict(int)
        max_urg = 1
        for it in items:
            t = it.get("triage", {})
            cat_counts[t.get("category", "other")] += 1
            max_urg = max(max_urg, int(t.get("urgency", 1)))
        top_cat = max(cat_counts, key=cat_counts.get)

        features.append({
            "type": "Feature",
            "properties": {
                "kind": _kind_for_category(top_cat),
                "category": top_cat,
                "count": len(items),
                "urgency": max_urg,
                "emoji": _emoji_for_kind(_kind_for_category(top_cat)),
                "hex": idx,
            },
            "geometry": {"type": "Point", "coordinates": [c_lon, c_lat]},
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": {
            "total_input": len(incidents),
            "hexes_after_k_anonymity": len(features),
            "resolution_m": res,
            "k": k,
            "virtual_city": virtual,
        },
    }


# ────────────────────────────────────────────
# /api/aggregate/supports（NGO/支援機関）
# ────────────────────────────────────────────

NGO_FILE = Path(__file__).parent.parent.parent.parent.parent.parent / "legalshield" / "knowledge" / "seeds" / "ngo_seed_geocoded.csv"


@router.get("/supports")
def list_supports(
    prefecture: str | None = Query(None),
    category: str | None = Query(None),
) -> dict[str, Any]:
    """NGO/支援機関を GeoJSON で返す"""
    import csv
    if not NGO_FILE.exists():
        return {"type": "FeatureCollection", "features": []}
    features = []
    with NGO_FILE.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if prefecture and row.get("prefecture") != prefecture:
                continue
            if category and row.get("category") != category:
                continue
            try:
                lat = float(row.get("latitude") or 0)
                lon = float(row.get("longitude") or 0)
            except ValueError:
                continue
            if lat == 0 and lon == 0:
                continue
            features.append({
                "type": "Feature",
                "properties": {
                    "name": row.get("name", ""),
                    "category": row.get("category", ""),
                    "phone": row.get("phone", ""),
                    "url": row.get("url", ""),
                    "is_24h": row.get("is_24h", "").lower() == "true",
                    "kind": _ngo_kind(row.get("category", "")),
                    "emoji": _emoji_for_kind(_ngo_kind(row.get("category", ""))),
                },
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
            })
    return {"type": "FeatureCollection", "features": features}


# ────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────

def _kind_for_category(cat: str) -> str:
    table = {
        "sexual_harassment": "predator",
        "stalking": "predator",
        "hidden_camera": "thief",
        "consumer_fraud": "fraud",
        "contract_trap": "fraud",
        "child_abuse": "abuse",
        "domestic_violence": "abuse",
        "school_bullying": "abuse",
        "elder_abuse": "abuse",
    }
    return table.get(cat, "other")


def _ngo_kind(cat: str) -> str:
    if "性暴力" in cat or "ワンストップ" in cat:
        return "onestop"
    if "児童" in cat or "子ども" in cat:
        return "jidoso"
    if "DV" in cat or "配偶者" in cat:
        return "ngo"
    if "弁護士" in cat or "法テラス" in cat:
        return "lawyer"
    if "外国" in cat:
        return "foreign"
    return "ngo"


def _emoji_for_kind(kind: str) -> str:
    return {
        "predator": "🐺",
        "thief": "😎",
        "fraud": "💼",
        "abuse": "🏚️",
        "police": "🚓",
        "ngo": "🏥",
        "jidoso": "🧸",
        "onestop": "🌸",
        "lawyer": "⚖️",
        "foreign": "🌐",
    }.get(kind, "📍")
