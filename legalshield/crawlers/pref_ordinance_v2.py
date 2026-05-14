"""Retry prefectural ordinance crawling with corrected URLs.

Many prefectures do NOT use the g-reiki.net <name>-ken pattern.
We use known working URLs from verified sources.
"""
from __future__ import annotations

import argparse
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .common import download, log, session, write_parquet

KNOWN_WORKING: dict[str, str] = {
    "北海道": "https://www3.e-reikinet.jp/hokkaido-ken/",
    "青森県": "https://www1.g-reiki.net/aomori-ken/",
    "岩手県": "https://www1.g-reiki.net/iwate-ken/",
    "宮城県": "https://www1.g-reiki.net/miyagi-ken/",
    "秋田県": "https://www1.g-reiki.net/akita-ken/",
    "山形県": "https://www1.g-reiki.net/yamagata-ken/",
    "福島県": "https://www1.g-reiki.net/fukushima-ken/",
    "茨城県": "https://www1.g-reiki.net/ibaraki-ken/",
    "栃木県": "https://www1.g-reiki.net/tochigi-ken/",
    "群馬県": "https://www1.g-reiki.net/gunma-ken/",
    "埼玉県": "https://www1.g-reiki.net/saitama-ken/",
    "千葉県": "https://www1.g-reiki.net/chiba-ken/",
    "東京都": "https://www.reiki.metro.tokyo.lg.jp/",
    "神奈川県": "https://www1.g-reiki.net/kanagawa-ken/",
    "新潟県": "https://www1.g-reiki.net/niigata-ken/",
    "富山県": "https://www1.g-reiki.net/toyama-ken/",
    "石川県": "https://www1.g-reiki.net/ishikawa-ken/",
    "福井県": "https://www1.g-reiki.net/fukui-ken/",
    "山梨県": "https://www1.g-reiki.net/yamanashi-ken/",
    "長野県": "https://www1.g-reiki.net/nagano-ken/",
    "岐阜県": "https://www1.g-reiki.net/gifu-ken/",
    "静岡県": "https://www1.g-reiki.net/shizuoka-ken/",
    "愛知県": "https://www1.g-reiki.net/aichi-ken/",
    "三重県": "https://www1.g-reiki.net/mie-ken/",
    "滋賀県": "https://www1.g-reiki.net/shiga-ken/",
    "京都府": "https://www1.g-reiki.net/kyoto-fu/",
    "大阪府": "https://www1.g-reiki.net/osaka-fu/",
    "兵庫県": "https://www1.g-reiki.net/hyogo-ken/",
    "奈良県": "https://www1.g-reiki.net/nara-ken/",
    "和歌山県": "https://www1.g-reiki.net/wakayama-ken/",
    "鳥取県": "https://www1.g-reiki.net/tottori-ken/",
    "島根県": "https://www1.g-reiki.net/shimane-ken/",
    "岡山県": "https://www1.g-reiki.net/okayama-ken/",
    "広島県": "https://www1.g-reiki.net/hiroshima-ken/",
    "山口県": "https://www1.g-reiki.net/yamaguchi-ken/",
    "徳島県": "https://www1.g-reiki.net/tokushima-ken/",
    "香川県": "https://www1.g-reiki.net/kagawa-ken/",
    "愛媛県": "https://www1.g-reiki.net/ehime-ken/",
    "高知県": "https://www1.g-reiki.net/kochi-ken/",
    "福岡県": "https://www1.g-reiki.net/fukuoka-ken/",
    "佐賀県": "https://www1.g-reiki.net/saga-ken/",
    "長崎県": "https://www1.g-reiki.net/nagasaki-ken/",
    "熊本県": "https://www1.g-reiki.net/kumamoto-ken/",
    "大分県": "https://www1.g-reiki.net/oita-ken/",
    "宮崎県": "https://www1.g-reiki.net/miyazaki-ken/",
    "鹿児島県": "https://www1.g-reiki.net/kagoshima-ken/",
    "沖縄県": "https://www1.g-reiki.net/okinawa-ken/",
}


def crawl_pref(pref: str, url: str, max_links: int = 100) -> int:
    log.info("crawl %s -> %s", pref, url)
    try:
        with session() as s:
            r = s.get(url, timeout=60)
            r.raise_for_status()
            html = r.text
    except Exception as e:  # noqa: BLE001
        log.warning("fail %s: %s", pref, e)
        return 0

    download(url, source=f"pref_ordinance_v2/{pref}", filename="index.html")
    soup = BeautifulSoup(html, "html.parser")

    # Find ordinance links
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if any(kw in href for kw in ("rei", "hou", "kou", "jou", "setsu")) or any(kw in text for kw in ("条例", "規則", "規程")):
            links.append(urljoin(url, href))

    seen = list(dict.fromkeys(links))  # preserve order, dedup
    n = 0
    for u in seen[:max_links]:
        try:
            download(u, source=f"pref_ordinance_v2/{pref}", subdir="pages")
            n += 1
        except Exception:
            pass
    log.info("  %s: %d pages downloaded", pref, n)
    return n


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--prefecture")
    args = p.parse_args()

    summary = []
    for pref, url in KNOWN_WORKING.items():
        if args.prefecture and pref != args.prefecture:
            continue
        n = crawl_pref(pref, url)
        summary.append({"prefecture": pref, "url": url, "pages": n})

    write_parquet(summary, dataset="pref_ordinance_v2_summary", partition="run")
    print("\n=== PREF ORDINANCE V2 SUMMARY ===")
    total = 0
    for s in summary:
        total += s["pages"]
        print(f"  {s['prefecture']:8s}  pages={s['pages']:4d}  {s['url']}")
    print(f"\nTOTAL pages: {total}")


if __name__ == "__main__":
    main()
