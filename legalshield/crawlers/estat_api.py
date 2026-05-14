"""e-Stat API client.

API spec: https://www.e-stat.go.jp/api/api-info/e-stat-manual

Required: set environment variable ESTAT_APP_ID with your application ID.
Get one at https://www.e-stat.go.jp/api/ (free, takes ~5 minutes).

Usage:
    python -m legalshield.crawlers.estat_api list-stats --keyword 犯罪
    python -m legalshield.crawlers.estat_api fetch --statsDataId 0003411595
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from .common import download, log, write_parquet, session

BASE = "https://api.e-stat.go.jp/rest/3.0/app/json"


def _app_id() -> str:
    aid = os.environ.get("ESTAT_APP_ID")
    if not aid:
        log.error("ESTAT_APP_ID not set. Get one at https://www.e-stat.go.jp/api/")
        sys.exit(2)
    return aid


def list_stats(keyword: str, limit: int = 50) -> list[dict[str, Any]]:
    """Search statistics tables by keyword."""
    params = {
        "appId": _app_id(),
        "searchWord": keyword,
        "limit": limit,
    }
    with session() as s:
        r = s.get(f"{BASE}/getStatsList", params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
    items = (
        data.get("GET_STATS_LIST", {})
        .get("DATALIST_INF", {})
        .get("TABLE_INF", [])
    )
    if isinstance(items, dict):
        items = [items]
    def _s(v):
        if v is None:
            return None
        if isinstance(v, dict):
            return str(v.get("$"))
        return str(v)

    out = []
    for it in items:
        out.append({
            "id": _s(it.get("@id")),
            "title": _s(it.get("TITLE")),
            "stat_name": _s(it.get("STAT_NAME")),
            "gov_org": _s(it.get("GOV_ORG")),
            "survey_date": _s(it.get("SURVEY_DATE")),
            "updated_date": _s(it.get("UPDATED_DATE")),
        })
    return out


def fetch_stats_data(stats_data_id: str) -> dict[str, Any]:
    """Fetch a full statistics table by its ID."""
    params = {
        "appId": _app_id(),
        "statsDataId": stats_data_id,
        "metaGetFlg": "Y",
    }
    with session() as s:
        r = s.get(f"{BASE}/getStatsData", params=params, timeout=120)
        r.raise_for_status()
        return r.json()


def parse_to_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert e-Stat response to flat dict rows.

    Keeps category codes and labels resolved via CLASS_INF.
    """
    sd = payload.get("GET_STATS_DATA", {}).get("STATISTICAL_DATA", {})
    class_inf = sd.get("CLASS_INF", {}).get("CLASS_OBJ", [])
    if isinstance(class_inf, dict):
        class_inf = [class_inf]

    # Build code -> name maps for each category dimension (id like "cat01" "area" "time")
    label_map: dict[str, dict[str, str]] = {}
    for c in class_inf:
        cid = c.get("@id")
        cls = c.get("CLASS", [])
        if isinstance(cls, dict):
            cls = [cls]
        label_map[cid] = {x.get("@code"): x.get("@name") for x in cls}

    values = sd.get("DATA_INF", {}).get("VALUE", [])
    if isinstance(values, dict):
        values = [values]

    rows = []
    for v in values:
        row: dict[str, Any] = {"value": v.get("$")}
        for k, code in v.items():
            if k.startswith("@") and k != "@unit":
                dim = k[1:]
                row[f"{dim}_code"] = code
                row[f"{dim}_name"] = label_map.get(dim, {}).get(code)
            elif k == "@unit":
                row["unit"] = code
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser(description="e-Stat API client")
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list-stats", help="search tables by keyword")
    pl.add_argument("--keyword", required=True)
    pl.add_argument("--limit", type=int, default=50)

    pf = sub.add_parser("fetch", help="fetch one table by statsDataId")
    pf.add_argument("--statsDataId", required=True)
    pf.add_argument("--dataset", default="estat", help="parquet subfolder")

    args = p.parse_args()

    if args.cmd == "list-stats":
        items = list_stats(args.keyword, args.limit)
        for it in items:
            print(f"{it['id']}\t{it['gov_org']}\t{it['stat_name']}\t{it['title']}")
        log.info("found %d tables", len(items))

    elif args.cmd == "fetch":
        payload = fetch_stats_data(args.statsDataId)
        rows = parse_to_rows(payload)
        out = write_parquet(rows, dataset=args.dataset, partition=args.statsDataId)
        print(out)


if __name__ == "__main__":
    main()
