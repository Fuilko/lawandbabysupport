"""Scrape Japan Federation of Bar Associations (日弁連) lawyer search.

The site has a search-by-prefecture feature:
  https://www.nichibenren.or.jp/jfba_info/bengoshikai/

We extract links to each prefectural bar association, then crawl their
member-finder pages where available.

NOTE: 日弁連 itself doesn't list all ~50k lawyers directly; each prefectural
bar association has its own system. We collect index pages and outbound links
as seeds for deeper crawling.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .common import download, log, ROOT, session, write_parquet

INDEX_URL = "https://www.nichibenren.or.jp/jfba_info/bengoshikai/"


def crawl_index() -> list[dict]:
    log.info("crawl index %s", INDEX_URL)
    with session() as s:
        r = s.get(INDEX_URL, timeout=60)
        r.raise_for_status()
        html = r.text
    download(INDEX_URL, source="nichibenren", filename="index.html")
    soup = BeautifulSoup(html, "html.parser")

    rows = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        # Prefectural bar association links usually contain 弁護士会
        if "弁護士会" in text and len(text) <= 20:
            full = urljoin(INDEX_URL, href)
            rows.append({"prefecture": text.replace("弁護士会", "").strip(),
                         "name": text, "url": full})
    log.info("found %d bar associations", len(rows))
    return rows


def crawl_bengoshikai(pref: str, url: str) -> int:
    log.info("crawl %s -> %s", pref, url)
    try:
        with session() as s:
            r = s.get(url, timeout=60)
            r.raise_for_status()
            html = r.text
    except Exception as e:  # noqa: BLE001
        log.warning("fail %s: %s", pref, e)
        return 0
    download(url, source=f"nichibenren/{pref}", filename="index.html")
    soup = BeautifulSoup(html, "html.parser")

    # Find member search / list links
    links = []
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        if any(kw in text for kw in ("会員検索", "弁護士検索", "会員名簿", "弁護士名簿", "会員一覧")):
            links.append({"prefecture": pref, "text": text,
                          "href": urljoin(url, a["href"])})

    if links:
        write_parquet(links, dataset=f"nichibenren_{pref}_links", partition="run")
    log.info("  %s: search links=%d", pref, len(links))
    return len(links)


def main() -> None:
    bars = crawl_index()
    if not bars:
        print("[warn] no bar associations found")
        return

    summary = []
    for b in bars:
        n = crawl_bengoshikai(b["prefecture"], b["url"])
        summary.append({"prefecture": b["prefecture"], "url": b["url"], "search_links": n})

    write_parquet(bars, dataset="nichibenren_bars", partition="run")
    write_parquet(summary, dataset="nichibenren_summary", partition="run")
    print("\n=== NICHI-BENREN SUMMARY ===")
    for s in summary:
        print(f"  {s['prefecture']:8s}  links={s['search_links']}")


if __name__ == "__main__":
    main()
