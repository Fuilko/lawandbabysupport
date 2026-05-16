"""Batch fetch priority datasets from e-Stat for PoC v1.

Strategy:
1. Search keywords -> collect statsDataIds
2. Fetch each table -> Parquet under knowledge/parsed/<dataset>/
3. Print summary

Run:
    python -m legalshield.crawlers.batch_fetch
"""
from __future__ import annotations

import time
from typing import Iterable

from .common import log, write_parquet
from . import estat_api

# (dataset_name, keyword, max_tables, agency_filter or None)
PLAN: list[tuple[str, str, int, str | None]] = [
    ("crime_npa",        "犯罪統計", 30, "警察庁"),
    ("prosecution_moj",  "検察", 30, None),
    ("judicial_courts",  "司法統計", 20, None),
    ("special_fraud",    "特殊詐欺", 10, None),
    ("dv_consultation",  "配偶者", 10, None),
    ("child_abuse",      "児童虐待", 15, None),
    ("suicide_stats",    "自殺", 15, None),
    ("consumer_pio",     "消費生活", 15, None),
    ("sexual_violence",  "性犯罪", 10, None),
    ("labor_dispute",    "労働紛争", 10, None),
    ("bullying_mext",    "いじめ", 10, None),
    ("elderly_abuse",    "高齢者虐待", 10, None),
    ("foreign_residents","在留外国人", 10, None),
    ("disability_consult","障害者", 10, None),
    ("hate_crime",       "ヘイト", 5, None),
    ("recidivism",       "再犯", 10, None),
    ("youth_crime",      "少年", 15, None),
    ("legal_aid",        "法テラス", 5, None),
    ("administrative_review","行政不服", 5, None),
]


def filter_items(items: list[dict], agency: str | None) -> list[dict]:
    if not agency:
        return items
    return [it for it in items if (it.get("gov_org") or "").startswith(agency)]


def fetch_dataset(dataset: str, keyword: str, max_n: int, agency: str | None) -> dict:
    log.info("=== %s : keyword=%s agency=%s ===", dataset, keyword, agency)
    items = estat_api.list_stats(keyword, limit=200)
    items = filter_items(items, agency)[:max_n]
    log.info("planning to fetch %d tables for %s", len(items), dataset)

    # Save the catalog itself
    write_parquet(items, dataset=f"{dataset}_catalog", partition="catalog")

    ok, fail = 0, 0
    for it in items:
        sid = it["id"]
        if not sid:
            continue
        try:
            payload = estat_api.fetch_stats_data(sid)
            rows = estat_api.parse_to_rows(payload)
            if rows:
                write_parquet(rows, dataset=dataset, partition=sid)
                ok += 1
            else:
                log.warning("empty rows for %s", sid)
            time.sleep(1.0)
        except Exception as e:  # noqa: BLE001
            log.warning("fail %s: %s", sid, e)
            fail += 1
    log.info("=== %s done: ok=%d fail=%d ===", dataset, ok, fail)
    return {"dataset": dataset, "ok": ok, "fail": fail, "planned": len(items)}


def main() -> None:
    summary = []
    for dataset, kw, n, agency in PLAN:
        try:
            summary.append(fetch_dataset(dataset, kw, n, agency))
        except Exception as e:  # noqa: BLE001
            log.error("dataset %s aborted: %s", dataset, e)
            summary.append({"dataset": dataset, "ok": 0, "fail": -1, "planned": 0})
    print("\n=== BATCH SUMMARY ===")
    for s in summary:
        print(f"  {s['dataset']:24s}  ok={s['ok']:3d}  fail={s['fail']:3d}  planned={s['planned']}")
    write_parquet(summary, dataset="batch_summary", partition="run")


if __name__ == "__main__":
    main()
