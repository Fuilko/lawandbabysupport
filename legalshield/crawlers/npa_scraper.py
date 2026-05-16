"""National Police Agency (警察庁) statistics scraper.

Strategy: NPA publishes annual / monthly statistics as Excel + PDF on
https://www.npa.go.jp/publications/statistics/ . We crawl the index pages,
download Excel files (preferred over PDF), and let a downstream parser
turn each workbook into Parquet.

This crawler ONLY downloads + records SHA256 in the manifest. Parsing is in
parsers/npa_*.py because each table has a different shape.

Usage:
    python -m legalshield.crawlers.npa_scraper crawl --section sousa
    python -m legalshield.crawlers.npa_scraper crawl --section tokushu_sagi
"""
from __future__ import annotations

import argparse
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .common import download, log, session

# Section -> seed index URL on npa.go.jp
SECTIONS: dict[str, str] = {
    # 犯罪統計（罪種別・都道府県別の月次/年次）
    "sousa":         "https://www.npa.go.jp/publications/statistics/sousa/index.html",
    # 特殊詐欺
    "tokushu_sagi":  "https://www.npa.go.jp/bureau/criminal/souni/tokusyusagi/index.html",
    # 自殺統計
    "jisatsu":       "https://www.npa.go.jp/publications/statistics/safetylife/jisatsu.html",
    # 交通事故統計
    "koutsuu":       "https://www.npa.go.jp/publications/statistics/koutsuu/toukei.html",
    # 生活安全（性犯罪含む）
    "seian":         "https://www.npa.go.jp/publications/statistics/safetylife/index.html",
}

EXCEL_RX = re.compile(r"\.(xlsx?|xls)$", re.IGNORECASE)
PDF_RX = re.compile(r"\.pdf$", re.IGNORECASE)


def crawl_section(section: str, max_files: int = 200) -> int:
    if section not in SECTIONS:
        raise SystemExit(f"unknown section: {section} (choose from {list(SECTIONS)})")

    url = SECTIONS[section]
    log.info("crawl %s -> %s", section, url)
    with session() as s:
        r = s.get(url, timeout=60)
        r.raise_for_status()
        html = r.text

    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if EXCEL_RX.search(href) or PDF_RX.search(href):
            links.append(urljoin(url, href))

    # de-dup, preserve order
    seen, ordered = set(), []
    for u in links:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    log.info("found %d candidate files", len(ordered))

    n = 0
    for u in ordered[:max_files]:
        try:
            download(u, source=f"npa/{section}", note=f"index={url}")
            n += 1
        except Exception as e:  # noqa: BLE001
            log.warning("skip %s (%s)", u, e)
    log.info("downloaded %d files for section=%s", n, section)
    return n


def main() -> None:
    p = argparse.ArgumentParser(description="NPA scraper")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("crawl")
    pc.add_argument("--section", required=True, choices=list(SECTIONS))
    pc.add_argument("--max", type=int, default=200)

    pl = sub.add_parser("list-sections")

    args = p.parse_args()
    if args.cmd == "list-sections":
        for k, v in SECTIONS.items():
            print(f"{k}\t{v}")
    elif args.cmd == "crawl":
        crawl_section(args.section, max_files=args.max)


if __name__ == "__main__":
    main()
