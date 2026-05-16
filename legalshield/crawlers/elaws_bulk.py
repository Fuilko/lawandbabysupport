"""Bulk-download every law body XML from e-Gov e-LAWS.

Reads the previously saved index (parsed/elaws_index/type_1.parquet),
fetches each law body, stores under knowledge/raw/elaws/lawdata/<law_id>.xml,
records SHA256 in manifest.jsonl, and saves a compact metadata Parquet.
"""
from __future__ import annotations

import argparse
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

from .common import RAW, ROOT, download, log, write_parquet
from . import elaws_api

INDEX_PARQUET = ROOT / "knowledge" / "parsed" / "elaws_index" / "type_1.parquet"
BODY_DIR = RAW / "elaws" / "lawdata"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=0, help="0 = all")
    p.add_argument("--sleep", type=float, default=0.4)
    p.add_argument("--start", type=int, default=0)
    args = p.parse_args()

    if not INDEX_PARQUET.exists():
        raise SystemExit(f"index not found: {INDEX_PARQUET}; run elaws_api list --save first")
    df = pd.read_parquet(INDEX_PARQUET)
    log.info("index has %d laws", len(df))

    rows = df.iloc[args.start:]
    if args.limit:
        rows = rows.head(args.limit)

    BODY_DIR.mkdir(parents=True, exist_ok=True)
    ok, fail, cached = 0, 0, 0
    for i, r in enumerate(rows.itertuples(index=False), 1):
        law_id = r.law_id
        if not law_id:
            continue
        target = BODY_DIR / f"{law_id}.xml"
        if target.exists() and target.stat().st_size > 500:
            cached += 1
            continue
        try:
            elaws_api.fetch_law(law_id)
            ok += 1
        except Exception as e:  # noqa: BLE001
            log.warning("fail %s: %s", law_id, e)
            fail += 1
        if i % 100 == 0:
            log.info("progress %d/%d  ok=%d fail=%d cached=%d", i, len(rows), ok, fail, cached)
        time.sleep(args.sleep)

    log.info("DONE  ok=%d fail=%d cached=%d  total=%d", ok, fail, cached, len(rows))


if __name__ == "__main__":
    main()
