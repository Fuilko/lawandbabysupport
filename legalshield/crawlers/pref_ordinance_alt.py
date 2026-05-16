"""Crawl prefectural ordinances from alternative unified portal (g-reiki.net).

Most prefectures share the g-reiki.net platform with pattern:
  https://www1.g-reiki.net/{pref}-ken/

But some use e-reikinet.jp or own domains.
This script uses a hybrid approach: try g-reiki first, fallback to known alts.
"""
from __future__ import annotations

import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .common import download, log, session, write_parquet

PREF_URLS = {
    "北海道": "https://www3.e-reikinet.jp/hokkaido-ken/",
    "青森県": "https://www1.g-reiki.net/aomori-ken/reiki_honbun/",
    "岩手県": "https://www1.g-reiki.net/iwate-ken/reiki_honbun/",
    "宮城県": "https://www1.g-reiki.net/miyagi-ken/reiki_honbun/",
    "秋田県": "https://www1.g-reiki.net/akita-ken/reiki_honbun/",
    "山形県": "https://www1.g-reiki.net/yamagata-ken/reiki_honbun/",
    "福島県": "https://www1.g-reiki.net/fukushima-ken/reiki_honbun/",
    "茨城県": "https://www1.g-reiki.net/ibaraki-ken/reiki_honbun/",
    "栃木県": "https://www1.g-reiki.net/tochigi-ken/reiki_honbun/",
    "群馬県": "https://www1.g-reiki.net/gunma-ken/reiki_honbun/",
    "埼玉県": "https://www1.g-reiki.net/saitama-ken/reiki_honbun/",
    "千葉県": "https://www1.g-reiki.net/chiba-ken/reiki_honbun/",
    "東京都": "https://www.reiki.metro.tokyo.lg.jp/",
    "神奈川県": "https://www1.g-reiki.net/kanagawa-ken/reiki_honbun/",
    "新潟県": "https://www1.g-reiki.net/niigata-ken/reiki_honbun/",
    "富山県": "https://www1.g-reiki.net/toyama-ken/reiki_honbun/",
    "石川県": "https://www1.g-reiki.net/ishikawa-ken/reiki_honbun/",
    "福井県": "https://www1.g-reiki.net/fukui-ken/reiki_honbun/",
    "山梨県": "https://www1.g-reiki.net/yamanashi-ken/reiki_honbun/",
    "長野県": "https://www1.g-reiki.net/nagano-ken/reiki_honbun/",
    "岐阜県": "https://www1.g-reiki.net/gifu-ken/reiki_honbun/",
    "静岡県": "https://www1.g-reiki.net/shizuoka-ken/reiki_honbun/",
    "愛知県": "https://www1.g-reiki.net/aichi-ken/reiki_honbun/",
    "三重県": "https://www1.g-reiki.net/mie-ken/reiki_honbun/",
    "滋賀県": "https://www1.g-reiki.net/shiga-ken/reiki_honbun/",
    "京都府": "https://www1.g-reiki.net/kyoto-fu/reiki_honbun/",
    "大阪府": "https://www1.g-reiki.net/osaka-fu/reiki_honbun/",
    "兵庫県": "https://www1.g-reiki.net/hyogo-ken/reiki_honbun/",
    "奈良県": "https://www1.g-reiki.net/nara-ken/reiki_honbun/",
    "和歌山県": "https://www1.g-reiki.net/wakayama-ken/reiki_honbun/",
    "鳥取県": "https://www1.g-reiki.net/tottori-ken/reiki_honbun/",
    "島根県": "https://www1.g-reiki.net/shimane-ken/reiki_honbun/",
    "岡山県": "https://www1.g-reiki.net/okayama-ken/reiki_honbun/",
    "広島県": "https://www1.g-reiki.net/hiroshima-ken/reiki_honbun/",
    "山口県": "https://www1.g-reiki.net/yamaguchi-ken/reiki_honbun/",
    "徳島県": "https://www1.g-reiki.net/tokushima-ken/reiki_honbun/",
    "香川県": "https://www1.g-reiki.net/kagawa-ken/reiki_honbun/",
    "愛媛県": "https://www1.g-reiki.net/ehime-ken/reiki_honbun/",
    "高知県": "https://www1.g-reiki.net/kochi-ken/reiki_honbun/",
    "福岡県": "https://www1.g-reiki.net/fukuoka-ken/reiki_honbun/",
    "佐賀県": "https://www1.g-reiki.net/saga-ken/reiki_honbun/",
    "長崎県": "https://www1.g-reiki.net/nagasaki-ken/reiki_honbun/",
    "熊本県": "https://www1.g-reiki.net/kumamoto-ken/reiki_honbun/",
    "大分県": "https://www1.g-reiki.net/oita-ken/reiki_honbun/",
    "宮崎県": "https://www1.g-reiki.net/miyazaki-ken/reiki_honbun/",
    "鹿児島県": "https://www1.g-reiki.net/kagoshima-ken/reiki_honbun/",
    "沖縄県": "https://www1.g-reiki.net/okinawa-ken/reiki_honbun/",
}


def crawl_pref(pref: str, url: str) -> dict:
    log.info("crawl %s -> %s", pref, url)
    try:
        with session() as s:
            r = s.get(url, timeout=60)
            r.raise_for_status()
            html = r.text
    except Exception as e:
        log.warning("fail %s: %s", pref, e)
        return {"prefecture": pref, "url": url, "status": "fetch_fail", "ordinances": 0}

    soup = BeautifulSoup(html, "html.parser")
    # g-reiki structure: rows with ordinance links
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if any(kw in href for kw in ("reiki_honbun", "lawId", "lawNum")) or any(kw in text for kw in ("条例", "規則", "規程")):
            links.append({"prefecture": pref, "text": text[:60], "href": urljoin(url, href)})

    log.info("  %s: found %d ordinance links", pref, len(links))
    return {"prefecture": pref, "url": url, "status": "ok", "ordinances": len(links), "links": links}


def main() -> None:
    summary = []
    all_links = []
    for pref, url in PREF_URLS.items():
        result = crawl_pref(pref, url)
        summary.append({"prefecture": result["prefecture"], "url": result["url"], "status": result["status"], "ordinances": result["ordinances"]})
        all_links.extend(result.get("links", []))
        time.sleep(0.3)

    write_parquet(summary, dataset="pref_ordinance_alt_summary", partition="run")
    if all_links:
        write_parquet(all_links, dataset="pref_ordinance_alt_links", partition="run")

    print("\n=== PREF ORDINANCE ALT SUMMARY ===")
    total = 0
    for s in summary:
        total += s["ordinances"]
        print(f"  {s['prefecture']:8s}  {s['status']:12s}  links={s['ordinances']:4d}  {s['url']}")
    print(f"\nTOTAL ordinance links: {total}")


if __name__ == "__main__":
    main()
