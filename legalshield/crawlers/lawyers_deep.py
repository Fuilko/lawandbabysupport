"""Deep crawl individual law offices from prefectural bar association sites.

Uses nichibenren member search as the entry point:
  https://www.nichibenren.or.jp/member_search/

Each bar association also has its own member finder.
We collect as many individual office listings as possible.
"""
from __future__ import annotations

import csv
import time
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .common import download, log, session, write_parquet

# 日弁連全国弁護士検索
MEMBER_SEARCH = "https://www.nichibenren.or.jp/member_search/"

# Known search-by-prefecture pattern (POST or GET)
PREF_CODES = {
    "北海道": "01", "青森県": "02", "岩手県": "03", "宮城県": "04", "秋田県": "05",
    "山形県": "06", "福島県": "07", "茨城県": "08", "栃木県": "09", "群馬県": "10",
    "埼玉県": "11", "千葉県": "12", "東京都": "13", "神奈川県": "14", "新潟県": "15",
    "富山県": "16", "石川県": "17", "福井県": "18", "山梨県": "19", "長野県": "20",
    "岐阜県": "21", "静岡県": "22", "愛知県": "23", "三重県": "24", "滋賀県": "25",
    "京都府": "26", "大阪府": "27", "兵庫県": "28", "奈良県": "29", "和歌山県": "30",
    "鳥取県": "31", "島根県": "32", "岡山県": "33", "広島県": "34", "山口県": "35",
    "徳島県": "36", "香川県": "37", "愛媛県": "38", "高知県": "39", "福岡県": "40",
    "佐賀県": "41", "長崎県": "42", "熊本県": "43", "大分県": "44", "宮崎県": "45",
    "鹿児島県": "46", "沖縄県": "47",
}


def search_by_prefecture(pref: str, code: str) -> list[dict]:
    """Try to search members by prefecture via nichibenren."""
    log.info("search lawyers %s (code=%s)", pref, code)
    # The actual search endpoint varies; try known patterns
    urls_to_try = [
        f"https://www.nichibenren.or.jp/member_search/?prefecture={code}",
        f"https://www.nichibenren.or.jp/member_search/?area={code}",
    ]
    for url in urls_to_try:
        try:
            with session() as s:
                r = s.get(url, timeout=30)
                r.raise_for_status()
                html = r.text
            soup = BeautifulSoup(html, "html.parser")
            # Look for result rows (names, offices, addresses)
            rows = []
            for tr in soup.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) >= 2:
                    name = tds[0].get_text(strip=True)
                    office = tds[1].get_text(strip=True) if len(tds) > 1 else ""
                    if name and len(name) < 40:
                        rows.append({"prefecture": pref, "name": name, "office": office[:60]})
            if rows:
                log.info("  %s: found %d results via %s", pref, len(rows), url)
                return rows
        except Exception as e:
            log.debug("skip %s: %s", url, e)
            continue
    log.info("  %s: no results", pref)
    return []


def crawl_bar_site(pref: str, url: str) -> list[dict]:
    """Crawl individual bar association member list page if available."""
    try:
        with session() as s:
            r = s.get(url, timeout=30)
            r.raise_for_status()
            html = r.text
        soup = BeautifulSoup(html, "html.parser")
        # Look for 会員名簿 or 弁護士一覧 links
        results = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if any(kw in text for kw in ("会員名簿", "弁護士一覧", "会員検索", "弁護士検索")):
                results.append({"prefecture": pref, "source": "bar_site", "text": text, "href": urljoin(url, a["href"])})
        return results
    except Exception as e:
        log.debug("crawl_bar_site %s: %s", pref, e)
        return []


def main() -> None:
    summary = []
    all_results = []

    # Strategy 1: nichibenren member search by prefecture
    for pref, code in PREF_CODES.items():
        rows = search_by_prefecture(pref, code)
        if rows:
            all_results.extend(rows)
        summary.append({"prefecture": pref, "source": "nichibenren", "count": len(rows)})
        time.sleep(0.5)

    # Strategy 2: bar association sites from seed
    seed = Path(__file__).resolve().parents[1] / "knowledge" / "seeds" / "bar_associations.csv"
    if seed.exists():
        with open(seed, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                links = crawl_bar_site(row["prefecture"], row["url"])
                all_results.extend(links)
                summary.append({"prefecture": row["prefecture"], "source": "bar_site", "count": len(links)})

    if all_results:
        write_parquet(all_results, dataset="lawyers_deep_results", partition="run")
    write_parquet(summary, dataset="lawyers_deep_summary", partition="run")

    print("\n=== LAWYERS DEEP CRAWL SUMMARY ===")
    total = sum(s["count"] for s in summary)
    for s in summary[:20]:
        print(f"  {s['prefecture']:8s}  {s['source']:12s}  count={s['count']}")
    print(f"\nTOTAL results: {total}")


if __name__ == "__main__":
    main()
