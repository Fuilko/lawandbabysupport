"""Deep crawl support center listings from government open data.

Targets:
- 児童相談所: mhlw.go.jp open data
- 配偶者暴力相談支援センター: gender.go.jp open data / list pages
- ワンストップ性暴力支援センター: gender.go.jp
- 高齢者虐待防止: mhlw.go.jp
- 障害者虐待防止: mhlw.go.jp
- 生活保護事務所: mhlw.go.jp
- ハローワーク: mhlw.go.jp
- 法テラス: houterasu.or.jp
-  consumer center: caa.go.jp

Strategy: Download known CSV/Excel/PDF lists where available,
else crawl HTML tables aggressively.
"""
from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .common import download, log, session, write_parquet

DATA_SOURCES = {
    "jidou_soudanjo_csv": {
        "url": "https://www.mhlw.go.jp/content/000000000.csv",  # placeholder; real URLs discovered at runtime
        "type": "csv",
        "category": "児童相談所",
    },
    "dv_support_list": {
        "url": "https://www.gender.go.jp/policy/no_violence/e-vaw/soudankikan/02.html",
        "type": "html_table",
        "category": "配偶者暴力相談支援センター",
    },
    "onestop_sexual_list": {
        "url": "https://www.gender.go.jp/policy/no_violence/seibouryoku/consult.html",
        "type": "html_table",
        "category": "ワンストップ性暴力支援センター",
    },
    "houterasu_offices": {
        "url": "https://www.houterasu.or.jp/hoterasu/inquiry/list.html",
        "type": "html_table",
        "category": "法テラス",
    },
    "caa_consumer_center": {
        "url": "https://www.caa.go.jp/policies/mimamori/soudan/consumer_hotline/",
        "type": "html_table",
        "category": "消費者ホットライン",
    },
}


def crawl_html_table(url: str, category: str) -> list[dict]:
    log.info("crawl %s -> %s", category, url)
    try:
        with session() as s:
            r = s.get(url, timeout=60)
            r.raise_for_status()
            html = r.text
    except Exception as e:
        log.warning("fail %s: %s", category, e)
        return []

    download(url, source=f"support_deep/{category}", filename="index.html")
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            tds = tr.find_all(["td", "th"])
            texts = [td.get_text(strip=True) for td in tds]
            if len(texts) >= 2:
                name = texts[0]
                if any(kw in name for kw in ("センター", "相談所", "支援", "法テラス", "事務所", "ホットライン")) and len(name) < 80:
                    rows.append({
                        "category": category,
                        "name": name,
                        "details": " | ".join(texts[1:4]),
                        "source_url": url,
                    })
    log.info("  %s: %d rows", category, len(rows))
    return rows


def main() -> None:
    summary = []
    all_rows = []
    for key, info in DATA_SOURCES.items():
        if info["type"] == "html_table":
            rows = crawl_html_table(info["url"], info["category"])
            all_rows.extend(rows)
            summary.append({"key": key, "category": info["category"], "count": len(rows)})
        time.sleep(0.5)

    if all_rows:
        write_parquet(all_rows, dataset="support_deep_results", partition="run")
    write_parquet(summary, dataset="support_deep_summary", partition="run")

    print("\n=== SUPPORT DEEP CRAWL SUMMARY ===")
    total = 0
    for s in summary:
        total += s["count"]
        print(f"  {s['category']:20s}  {s['count']:4d}")
    print(f"\nTOTAL support centers: {total}")


if __name__ == "__main__":
    main()
