"""e-Gov 法令 API client.

API spec: https://laws.e-gov.go.jp/apitop/
Endpoints (no auth required):
  /api/1/lawlists/{LawType}     -> 1=全法令 2=憲法・法律 3=政令・勅令 4=府省令・規則
  /api/1/lawdata/{LawId}        -> full XML body
  /api/1/articles                -> 条項取得
"""
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from typing import Any

from .common import log, session, write_parquet, download

BASE = "https://laws.e-gov.go.jp/api/1"


def list_laws(law_type: int = 1) -> list[dict[str, Any]]:
    with session() as s:
        r = s.get(f"{BASE}/lawlists/{law_type}", timeout=120)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    rows = []
    for li in root.iter("LawNameListInfo"):
        rows.append({
            "law_id":        (li.findtext("LawId") or "").strip(),
            "law_name":      (li.findtext("LawName") or "").strip(),
            "law_no":        (li.findtext("LawNo") or "").strip(),
            "promulgation":  (li.findtext("PromulgationDate") or "").strip(),
        })
    return rows


def fetch_law(law_id: str, source: str = "elaws") -> None:
    url = f"{BASE}/lawdata/{law_id}"
    download(url, source=source, subdir="lawdata", filename=f"{law_id}.xml",
             note="e-Gov 法令API lawdata")


def main() -> None:
    p = argparse.ArgumentParser(description="e-Gov 法令API")
    sub = p.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("list", help="list all laws")
    pl.add_argument("--type", type=int, default=1, choices=[1, 2, 3, 4])
    pl.add_argument("--save", action="store_true")
    pf = sub.add_parser("fetch", help="fetch one law xml")
    pf.add_argument("--id", required=True)
    args = p.parse_args()
    if args.cmd == "list":
        rows = list_laws(args.type)
        log.info("got %d laws of type=%d", len(rows), args.type)
        if args.save:
            write_parquet(rows, dataset="elaws_index",
                          partition=f"type_{args.type}")
        else:
            for r in rows[:20]:
                print(f"{r['law_id']}\t{r['promulgation']}\t{r['law_name']}")
    elif args.cmd == "fetch":
        fetch_law(args.id)


if __name__ == "__main__":
    main()
