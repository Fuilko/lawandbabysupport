"""Crawl prefectural ordinances directly from each prefecture's official ordinance portal.

Uses known official URLs (verified 2024-2025) instead of g-reiki.net.
Fetches the top-level ordinance index pages as HTML.
"""
from __future__ import annotations

import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .common import download, log, session, write_parquet

OFFICIAL_ORDINANCE_URLS = {
    "北海道": "https://www3.e-reikinet.jp/hokkaido-ken/",
    "青森県": "https://www.pref.aomori.lg.jp/reiki/reiki_index.html",
    "岩手県": "https://www.pref.iwate.jp/kensei/reiki/index.html",
    "宮城県": "https://www.pref.miyagi.jp/kensei/reiki/",
    "秋田県": "https://www.pref.akita.lg.jp/kensei/reiki/index.html",
    "山形県": "https://www.pref.yamagata.jp/030026/reiki/index.html",
    "福島県": "https://www.pref.fukushima.lg.jp/kensei/reiki/",
    "茨城県": "https://www.pref.ibaraki.jp/kensei/reiki/",
    "栃木県": "https://www.pref.tochigi.lg.jp/kensei/reiki/",
    "群馬県": "https://www.pref.gunma.jp/kensei/reiki/",
    "埼玉県": "https://www.pref.saitama.lg.jp/a0801/reiki/index.html",
    "千葉県": "https://www.pref.chiba.lg.jp/kensei/reiki/",
    "東京都": "https://www.reiki.metro.tokyo.lg.jp/",
    "神奈川県": "https://www.pref.kanagawa.jp/kensei/reiki/",
    "新潟県": "https://www.pref.niigata.lg.jp/kensei/reiki/",
    "富山県": "https://www.pref.toyama.jp/kensei/reiki/",
    "石川県": "https://www.pref.ishikawa.lg.jp/kensei/reiki.html",
    "福井県": "https://www.pref.fukui.lg.jp/kensei/reiki/",
    "山梨県": "https://www.pref.yamanashi.jp/kensei/reiki/",
    "長野県": "https://www.pref.nagano.lg.jp/kensei/reiki/",
    "岐阜県": "https://www.pref.gifu.lg.jp/kensei/reiki/",
    "静岡県": "https://www.pref.shizuoka.jp/kensei/reiki/",
    "愛知県": "https://www.pref.aichi.jp/kensei/reiki/",
    "三重県": "https://www.pref.mie.lg.jp/kensei/reiki/",
    "滋賀県": "https://www.pref.shiga.lg.jp/kensei/reiki/",
    "京都府": "https://www.pref.kyoto.jp/kensei/reiki/",
    "大阪府": "https://www.pref.osaka.lg.jp/kensei/reiki/",
    "兵庫県": "https://web.pref.hyogo.lg.jp/kensei/reiki/",
    "奈良県": "https://www.pref.nara.jp/kensei/reiki/",
    "和歌山県": "https://www.pref.wakayama.lg.jp/kensei/reiki/",
    "鳥取県": "https://www.pref.tottori.lg.jp/kensei/reiki/",
    "島根県": "https://www.pref.shimane.lg.jp/kensei/reiki/",
    "岡山県": "https://www.pref.okayama.jp/kensei/reiki/",
    "広島県": "https://www.pref.hiroshima.lg.jp/kensei/reiki/",
    "山口県": "https://www.pref.yamaguchi.lg.jp/kensei/reiki/",
    "徳島県": "https://www.pref.tokushima.lg.jp/kensei/reiki/",
    "香川県": "https://www.pref.kagawa.lg.jp/kensei/reiki/",
    "愛媛県": "https://www.pref.ehime.jp/kensei/reiki/",
    "高知県": "https://www.pref.kochi.lg.jp/kensei/reiki/",
    "福岡県": "https://www.pref.fukuoka.lg.jp/kensei/reiki/",
    "佐賀県": "https://www.pref.saga.lg.jp/kensei/reiki/",
    "長崎県": "https://www.pref.nagasaki.jp/kensei/reiki/",
    "熊本県": "https://www.pref.kumamoto.jp/kensei/reiki/",
    "大分県": "https://www.pref.oita.jp/kensei/reiki/",
    "宮崎県": "https://www.pref.miyazaki.lg.jp/kensei/reiki/",
    "鹿児島県": "https://www.pref.kagoshima.jp/kensei/reiki/",
    "沖縄県": "https://www.pref.okinawa.jp/kensei/reiki/",
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

    download(url, source=f"pref_ordinance_direct/{pref}", filename="index.html")
    soup = BeautifulSoup(html, "html.parser")

    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if any(kw in text for kw in ("条例", "規則", "規程", "要綱", "要領")) and len(text) < 100:
            links.append({
                "prefecture": pref,
                "name": text[:80],
                "href": urljoin(url, href),
                "source_url": url,
            })

    log.info("  %s: %d links", pref, len(links))
    return {"prefecture": pref, "url": url, "status": "ok", "ordinances": len(links), "links": links}


def main() -> None:
    summary = []
    all_links = []
    for pref, url in OFFICIAL_ORDINANCE_URLS.items():
        result = crawl_pref(pref, url)
        summary.append({
            "prefecture": result["prefecture"],
            "url": result["url"],
            "status": result["status"],
            "ordinances": result["ordinances"],
        })
        all_links.extend(result.get("links", []))
        time.sleep(0.3)

    write_parquet(summary, dataset="pref_ordinance_direct_summary", partition="run")
    if all_links:
        write_parquet(all_links, dataset="pref_ordinance_direct_links", partition="run")

    print("\n=== PREF ORDINANCE DIRECT SUMMARY ===")
    total = 0
    ok_count = 0
    for s in summary:
        total += s["ordinances"]
        if s["status"] == "ok":
            ok_count += 1
        print(f"  {s['prefecture']:8s}  {s['status']:12s}  links={s['ordinances']:4d}")
    print(f"\nTOTAL links: {total}  from {ok_count}/47 prefectures")


if __name__ == "__main__":
    main()
