"""Parallel bulk fetch for e-LAWS using a thread pool.

Cuts wall-time from ~7h to ~30-60 min using 8 concurrent workers.
Stays polite: per-worker rate-limited at 1 req/sec → ~8 req/s total.
"""
from __future__ import annotations

import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from .common import RAW, ROOT, log, session, append_manifest, ManifestEntry, sha256_file
from datetime import datetime, timezone

INDEX_PARQUET = ROOT / "knowledge" / "parsed" / "elaws_index" / "type_1.parquet"
BODY_DIR = RAW / "elaws" / "lawdata"
BASE = "https://laws.e-gov.go.jp/api/1/lawdata"


def fetch_one(law_id: str, sleep_sec: float) -> tuple[str, str]:
    """Returns (status, law_id)."""
    target = BODY_DIR / f"{law_id}.xml"
    if target.exists() and target.stat().st_size > 500:
        return ("cached", law_id)
    url = f"{BASE}/{law_id}"
    try:
        with session() as s:
            r = s.get(url, timeout=120, stream=True)
            r.raise_for_status()
            with open(target, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 16):
                    if chunk:
                        f.write(chunk)
        time.sleep(sleep_sec)
        try:
            append_manifest(ManifestEntry(
                source="elaws_bulk_parallel",
                url=url,
                saved_to=str(target.relative_to(ROOT)),
                sha256=sha256_file(target),
                bytes=target.stat().st_size,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                content_type="application/xml",
            ))
        except Exception:
            pass
        return ("ok", law_id)
    except Exception as e:  # noqa: BLE001
        return (f"fail:{type(e).__name__}", law_id)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--sleep", type=float, default=1.0, help="per-worker pause")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--start", type=int, default=0)
    args = p.parse_args()

    BODY_DIR.mkdir(parents=True, exist_ok=True)
    if not INDEX_PARQUET.exists():
        raise SystemExit("index not found; run elaws_api list --save first")
    df = pd.read_parquet(INDEX_PARQUET)
    ids = [x for x in df["law_id"].tolist()[args.start:] if x]
    if args.limit:
        ids = ids[: args.limit]
    log.info("planning %d laws with %d workers", len(ids), args.workers)

    ok = cached = fail = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fetch_one, lid, args.sleep): lid for lid in ids}
        for i, fu in enumerate(as_completed(futs), 1):
            status, lid = fu.result()
            if status == "ok":
                ok += 1
            elif status == "cached":
                cached += 1
            else:
                fail += 1
            if i % 100 == 0:
                el = time.time() - t0
                rate = i / el if el else 0
                eta = (len(ids) - i) / rate if rate else 0
                log.info("progress %d/%d ok=%d cached=%d fail=%d  rate=%.1f/s eta=%.0fmin",
                         i, len(ids), ok, cached, fail, rate, eta / 60)
    log.info("DONE ok=%d cached=%d fail=%d total=%d elapsed=%.0fmin",
             ok, cached, fail, len(ids), (time.time() - t0) / 60)


if __name__ == "__main__":
    main()
