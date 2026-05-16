"""Facility-location crawlers (courts, police, lawyers, support centers).

Strategy
--------
1. Most authoritative pages list addresses but no machine-readable coords.
2. We crawl HTML pages, save raw, then parse addresses (Sleuth Kit-free).
3. Geocoding is done downstream (jageocoder offline or Yahoo OpenLocal API).

For PoC we hit the canonical index URLs for each facility type and dump
HTML + extract address blocks where simple selectors work.
"""
from __future__ import annotations

import argparse
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .common import download, log, session, write_parquet

ENDPOINTS: dict[str, str] = {
    # 裁判所
    "saibansho_index":   "https://www.courts.go.jp/saiban/index.html",
    "saibansho_list":    "https://www.courts.go.jp/about/zenkoku_db/index.html",
    # 検察庁
    "kensatsu_index":    "https://www.kensatsu.go.jp/kakuchou_kensatsu/",
    # 法テラス
    "houterasu_index":   "https://www.houterasu.or.jp/local_offices/",
    # 警察庁・都道府県警
    "npa_index":         "https://www.npa.go.jp/",
    "pref_police_list":  "https://www.npa.go.jp/policies/links/index.html",
    # 弁護士会
    "nichibenren":       "https://www.nichibenren.or.jp/jfba_info/bengoshikai/",
    # 児童相談所
    "jidousoudan":       "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kodomo/kodomo_kosodate/dv/about.html",
    # 配偶者暴力相談支援センター
    "dv_centers":        "https://www.gender.go.jp/policy/no_violence/e-vaw/soudankikan/02.html",
    # ワンストップ性暴力支援センター
    "onestop_sexual":    "https://www.gender.go.jp/policy/no_violence/seibouryoku/consult.html",
    # 公証役場
    "kosho":             "https://www.koshonin.gr.jp/list",
    # 司法書士会
    "shihoushoshi":      "https://www.shiho-shoshi.or.jp/",
    # 行政書士会
    "gyousei":           "https://www.gyosei.or.jp/",
}


ADDR_RX = re.compile(r"(〒\s*\d{3}-?\d{4}[\s　]*[^<\n]{5,80})")


def crawl(name: str, url: str) -> int:
    log.info("crawl %s -> %s", name, url)
    try:
        with session() as s:
            r = s.get(url, timeout=60)
            r.raise_for_status()
            html = r.text
    except Exception as e:  # noqa: BLE001
        log.warning("fail %s: %s", name, e)
        return 0

    download(url, source=f"facilities/{name}", filename="index.html")
    addrs = ADDR_RX.findall(html)
    soup = BeautifulSoup(html, "html.parser")

    rows = [{"name": name, "url": url, "address": a.strip()} for a in addrs]
    log.info("  addresses found: %d", len(rows))

    # Also save outbound facility links
    out_links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        text = a.get_text(strip=True)
        if text and len(text) <= 80 and any(
            kw in text for kw in ("裁判所", "検察庁", "弁護士会", "法テラス",
                                   "警察", "相談", "支援", "センター", "公証",
                                   "司法書士", "行政書士")
        ):
            out_links.append({"name": name, "text": text, "href": href})

    if rows:
        write_parquet(rows, dataset=f"facility_{name}_addrs", partition="run")
    if out_links:
        write_parquet(out_links, dataset=f"facility_{name}_links", partition="run")
    return len(rows) + len(out_links)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--only", help="endpoint name to crawl alone")
    args = p.parse_args()

    summary = []
    for name, url in ENDPOINTS.items():
        if args.only and name != args.only:
            continue
        n = crawl(name, url)
        summary.append({"endpoint": name, "url": url, "rows": n})
    write_parquet(summary, dataset="facilities_summary", partition="run")
    print("\n=== FACILITIES SUMMARY ===")
    for s in summary:
        print(f"  {s['endpoint']:22s}  rows={s['rows']:4d}  {s['url']}")


if __name__ == "__main__":
    main()
