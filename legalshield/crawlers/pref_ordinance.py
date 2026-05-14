"""Crawl 47 都道府県 ordinance lists from g-reiki.net (and a few outliers).

g-reiki.net is the de-facto unified ordinance portal used by ~40 prefectures.
This crawler pulls the top-level index page for each prefecture so we have
at minimum a discoverable seed; deeper crawling per page can be added later.
"""
from __future__ import annotations

import argparse
import csv
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .common import download, log, session, write_parquet, ROOT

SEED_CSV = ROOT / "knowledge" / "seeds" / "pref_ordinance_seed.csv"
LINK_RX = re.compile(r"/cgi-bin/cbgetinf\.exe|/reiki/|/houbun/|/r1/", re.IGNORECASE)


def load_seed() -> list[tuple[str, str]]:
    out = []
    with open(SEED_CSV, encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            if row.get("prefecture") and row.get("base_url"):
                out.append((row["prefecture"], row["base_url"]))
    return out


def crawl_index(prefecture: str, base_url: str, max_links: int = 200) -> int:
    log.info("crawl %s -> %s", prefecture, base_url)
    try:
        with session() as s:
            r = s.get(base_url, timeout=60)
            r.raise_for_status()
            html = r.text
    except Exception as e:  # noqa: BLE001
        log.warning("fail index %s: %s", prefecture, e)
        return 0

    # Save the index html itself
    download(base_url, source=f"pref_ordinance/{prefecture}", filename="index.html",
             note=f"pref ordinance index {prefecture}")

    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if LINK_RX.search(href):
            links.append(urljoin(base_url, href))

    seen, ordered = set(), []
    for u in links:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    log.info("  found %d ordinance-like links", len(ordered))

    # First-pass: just download the top max_links HTML pages (catalog / chapter pages)
    n = 0
    for u in ordered[:max_links]:
        try:
            download(u, source=f"pref_ordinance/{prefecture}", subdir="pages")
            n += 1
        except Exception as e:  # noqa: BLE001
            log.debug("skip %s (%s)", u, e)
    return n


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--prefecture", help="only this prefecture, e.g. 高知県")
    p.add_argument("--max", type=int, default=80)
    p.add_argument("--start", type=int, default=0)
    args = p.parse_args()

    seeds = load_seed()
    if args.prefecture:
        seeds = [(p_, u) for p_, u in seeds if p_ == args.prefecture]
    seeds = seeds[args.start:]

    summary = []
    for pref, url in seeds:
        if pref.startswith("全国"):
            continue
        n = crawl_index(pref, url, max_links=args.max)
        summary.append({"prefecture": pref, "url": url, "downloaded": n})
    write_parquet(summary, dataset="pref_ordinance_summary", partition="run")
    print("\n=== PREF ORDINANCE SUMMARY ===")
    for s in summary:
        print(f"  {s['prefecture']:8s}  files={s['downloaded']:4d}  {s['url']}")


if __name__ == "__main__":
    main()
