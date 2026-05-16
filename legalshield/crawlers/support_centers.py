"""Crawl national support-center listings from multiple ministries.

Targets:
- 児童相談所: mhlw.go.jp (厚労省)
- 配偶者暴力相談支援センター: gender.go.jp (内閣府)
- ワンストップ性暴力支援センター: gender.go.jp (内閣府)
- 高齢者虐待防止センター: mhlw.go.jp
- 障害者虐待防止センター: mhlw.go.jp
"""
from __future__ import annotations

import csv
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .common import download, log, ROOT, session, write_parquet

TARGETS = {
    "jidou_soudanjo": {
        "url": "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kodomo/kodomo_kosodate/dv/index.html",
        "name_kws": ["児童相談所", "相談所"],
    },
    "dv_support": {
        "url": "https://www.gender.go.jp/policy/no_violence/e-vaw/soudankikan/02.html",
        "name_kws": ["配偶者", "DV", "支援"],
    },
    "onestop_sexual": {
        "url": "https://www.gender.go.jp/policy/no_violence/seibouryoku/consult.html",
        "name_kws": ["ワンストップ", "性暴力", "支援"],
    },
    "elderly_abuse": {
        "url": "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000130871.html",
        "name_kws": ["高齢者", "虐待", "防止"],
    },
    "disability_abuse": {
        "url": "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/shougaihoken/shougaisha/abuse/index.html",
        "name_kws": ["障害者", "虐待", "防止"],
    },
}

ADDR_RX = re.compile(r"(〒\s*\d{3}-?\d{4}[\s　]*[^<\n]{5,80})")
TEL_RX  = re.compile(r"(0\d{1,4}-\d{1,4}-\d{4}|\d{10,11})")


def crawl_one(key: str, url: str, name_kws: list[str]) -> int:
    log.info("crawl %s -> %s", key, url)
    try:
        with session() as s:
            r = s.get(url, timeout=60)
            r.raise_for_status()
            html = r.text
    except Exception as e:  # noqa: BLE001
        log.warning("fail %s: %s", key, e)
        return 0

    download(url, source=f"support_centers/{key}", filename="index.html")
    soup = BeautifulSoup(html, "html.parser")

    # Strategy 1: table rows with address or tel
    rows = []
    for tr in soup.find_all("tr"):
        text = tr.get_text(" ", strip=True)
        if any(kw in text for kw in name_kws):
            addr = ADDR_RX.search(text)
            tel = TEL_RX.search(text)
            # Try to extract name from th/td
            name = ""
            for tag in ("th", "td", "a"):
                t = tr.find(tag)
                if t:
                    name = t.get_text(strip=True)
                    if len(name) > 3:
                        break
            rows.append({
                "type": key,
                "name": name[:80],
                "address": addr.group(1) if addr else None,
                "tel": tel.group(1) if tel else None,
                "source_url": url,
            })

    # Strategy 2: links to prefecture-specific pages
    out_links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        text = a.get_text(strip=True)
        if any(kw in text for kw in name_kws) and len(text) < 80:
            out_links.append({"type": key, "text": text, "href": href})

    if rows:
        write_parquet(rows, dataset=f"support_center_{key}", partition="run")
    if out_links:
        write_parquet(out_links, dataset=f"support_center_{key}_links", partition="run")
    total = len(rows) + len(out_links)
    log.info("  %s: rows=%d links=%d", key, len(rows), len(out_links))
    return total


def main() -> None:
    summary = []
    for key, info in TARGETS.items():
        n = crawl_one(key, info["url"], info["name_kws"])
        summary.append({"type": key, "rows": n, "url": info["url"]})
    write_parquet(summary, dataset="support_centers_summary", partition="run")
    print("\n=== SUPPORT CENTERS SUMMARY ===")
    for s in summary:
        print(f"  {s['type']:20s}  rows={s['rows']:4d}  {s['url']}")


if __name__ == "__main__":
    main()
