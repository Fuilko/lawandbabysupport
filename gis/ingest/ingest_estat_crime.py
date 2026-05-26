"""Ingest 警察庁オープンデータ / e-Stat 犯罪統計 (prefecture × month × type).

This MVP loader expects a CSV with columns:
  prefecture_code, year_month (YYYY-MM), crime_type, count

It aggregates to prefecture-level totals and (optionally) snaps to a 500-m
grid. The grid step is left to a future loader once the operator selects
a canonical mesh source (e.g. 第3次地域メッシュ from 統計地理情報システム).

For now, prefecture-level totals are written as one big "synthetic grid"
cell per prefecture so that the API endpoints have something to return.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

from sqlalchemy import text

from ingest.common import finish_run, logger, session_scope, start_run

DATASET = "estat_crime"


async def run(csv_path: Path) -> None:
    # Aggregate {(pref, year_month) : {crime_type: count}}
    agg: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    rows_in = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows_in += 1
            pc = (row.get("prefecture_code") or "").zfill(2)
            ym = (row.get("year_month") or "").strip()
            ct = (row.get("crime_type") or "unknown").strip()
            try:
                cnt = int(row.get("count") or 0)
            except ValueError:
                cnt = 0
            if not (pc and ym):
                continue
            agg[(pc, ym)][ct] += cnt

    async with session_scope() as s:
        run_id = await start_run(s, DATASET)
        rows_out = 0
        try:
            for (pc, ym), by_type in agg.items():
                grid_id = f"PREF-{pc}"   # synthetic grid until real mesh lands
                total = sum(by_type.values())
                # Use the prefecture polygon as the grid geom (simplification).
                pref = (
                    await s.execute(
                        text("SELECT geom::geometry AS g FROM legalshield.prefecture WHERE prefecture_code = :pc"),
                        {"pc": pc},
                    )
                ).first()
                if not pref:
                    logger.warning("prefecture %s missing — run N03 ingest first", pc)
                    continue
                # The prefecture polygon is a MULTIPOLYGON, but our grid_id schema
                # expects POLYGON. Fall back to its envelope for the synthetic cell.
                await s.execute(
                    text(
                        """
                        INSERT INTO legalshield.crime_grid
                          (grid_id, geom, year_month, total_count, by_type, prefecture_code)
                        SELECT
                          :gid,
                          ST_Envelope(geom::geometry)::geography,
                          :ym,
                          :total,
                          CAST(:bt AS jsonb),
                          :pc
                        FROM legalshield.prefecture
                        WHERE prefecture_code = :pc
                        ON CONFLICT (grid_id, year_month) DO UPDATE
                          SET total_count = EXCLUDED.total_count,
                              by_type     = EXCLUDED.by_type
                        """
                    ),
                    {
                        "gid": grid_id,
                        "ym": ym,
                        "total": total,
                        "bt": json.dumps(by_type, ensure_ascii=False),
                        "pc": pc,
                    },
                )
                rows_out += 1

            # Refresh the rolling 12-month MV
            await s.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY legalshield.crime_grid_12m"))
            await finish_run(s, run_id, "success", rows_in=rows_in, rows_out=rows_out)
            logger.info("estat_crime ingest done: in=%d out=%d", rows_in, rows_out)
        except Exception as exc:
            await finish_run(s, run_id, "failed", notes=repr(exc))
            raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    args = ap.parse_args()
    if not args.csv.exists():
        print(f"CSV not found: {args.csv}", file=sys.stderr)
        return 2
    asyncio.run(run(args.csv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
