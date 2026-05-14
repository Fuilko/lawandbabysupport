"""data.go.jp (Japanese Government CKAN) client.

CKAN API: https://www.data.go.jp/data/api/3/action/

Usage:
    python -m legalshield.crawlers.datagojp_ckan search --q 犯罪 --rows 50
    python -m legalshield.crawlers.datagojp_ckan show --id <package_id>
"""
from __future__ import annotations

import argparse
import json
from typing import Any

from .common import log, session, write_parquet

BASE = "https://www.data.go.jp/data/api/3/action"


def package_search(q: str, rows: int = 50, start: int = 0) -> dict[str, Any]:
    with session() as s:
        r = s.get(f"{BASE}/package_search", params={"q": q, "rows": rows, "start": start}, timeout=60)
        r.raise_for_status()
        return r.json()


def package_show(pkg_id: str) -> dict[str, Any]:
    with session() as s:
        r = s.get(f"{BASE}/package_show", params={"id": pkg_id}, timeout=60)
        r.raise_for_status()
        return r.json()


def main() -> None:
    p = argparse.ArgumentParser(description="data.go.jp CKAN client")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("search")
    ps.add_argument("--q", required=True)
    ps.add_argument("--rows", type=int, default=50)
    ps.add_argument("--save", action="store_true", help="save flat list as parquet")

    pw = sub.add_parser("show")
    pw.add_argument("--id", required=True)

    args = p.parse_args()

    if args.cmd == "search":
        res = package_search(args.q, rows=args.rows)
        results = res.get("result", {}).get("results", [])
        flat = []
        for it in results:
            flat.append({
                "id": it.get("id"),
                "name": it.get("name"),
                "title": it.get("title"),
                "organization": (it.get("organization") or {}).get("title"),
                "notes": (it.get("notes") or "")[:500],
                "num_resources": it.get("num_resources"),
                "metadata_modified": it.get("metadata_modified"),
            })
            print(f"{it.get('id')}\t{(it.get('organization') or {}).get('title')}\t{it.get('title')}")
        log.info("hits=%d", len(flat))
        if args.save:
            write_parquet(flat, dataset="datagojp_search", partition=f"q_{args.q}")

    elif args.cmd == "show":
        res = package_show(args.id)
        print(json.dumps(res, ensure_ascii=False, indent=2)[:5000])


if __name__ == "__main__":
    main()
