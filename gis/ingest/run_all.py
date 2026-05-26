"""Top-level dispatcher: `python -m ingest.run_all --datasets houterasu,n03,crime`

Picks the first matching CSV / SHP under data/raw/{dataset}/. For a clean
first deploy the operator places files there:

  data/raw/houterasu/houterasu_offices.csv
  data/raw/N03/N03-XXXXX.shp        (+ .dbf .shx .prj)
  data/raw/crime/estat_crime.csv
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from ingest import ingest_estat_crime, ingest_houterasu, ingest_n03_boundaries
from ingest.common import RAW_DIR, logger


async def run_houterasu() -> None:
    csv_files = list((RAW_DIR / "houterasu").glob("*.csv"))
    if not csv_files:
        logger.warning("no houterasu CSV under %s/houterasu/ — skipping", RAW_DIR)
        return
    await ingest_houterasu.run(csv_files[0])


async def run_n03() -> None:
    shps = list((RAW_DIR / "N03").glob("*.shp"))
    if not shps:
        logger.warning("no N03 .shp under %s/N03/ — skipping", RAW_DIR)
        return
    await ingest_n03_boundaries.run(shps[0])


async def run_crime() -> None:
    csvs = list((RAW_DIR / "crime").glob("*.csv"))
    if not csvs:
        logger.warning("no crime CSV under %s/crime/ — skipping", RAW_DIR)
        return
    await ingest_estat_crime.run(csvs[0])


JOBS = {
    "houterasu": run_houterasu,
    "n03":       run_n03,
    "crime":     run_crime,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default="n03,houterasu,crime",
                     help="comma-separated subset of: " + ",".join(JOBS))
    args = ap.parse_args()

    selected = [d.strip() for d in args.datasets.split(",") if d.strip()]
    unknown = [d for d in selected if d not in JOBS]
    if unknown:
        print(f"unknown dataset(s): {unknown}. valid: {list(JOBS)}", file=sys.stderr)
        return 2

    async def _run() -> None:
        # Order matters: N03 must run before crime (the latter joins on prefecture).
        for d in ["n03", "houterasu", "crime"]:
            if d in selected:
                logger.info("=== running %s ===", d)
                try:
                    await JOBS[d]()
                except Exception as exc:
                    logger.exception("%s failed: %r", d, exc)

    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
