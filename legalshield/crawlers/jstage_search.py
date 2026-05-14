"""J-STAGE Legal Paper Crawler — Search and fetch academic papers on crime/victim support.

J-STAGE hosts 4,000+ Japanese academic journals including legal journals:
- The Annals of Legal Philosophy (jalp1953)
- Legal History Review (jalha)
- Various criminology, psychology, and sociology journals

Usage:
    python jstage_search.py --query "DV 被害者 支援" --max 20
    python jstage_search.py --query "判例 性犯罪 同意" --max 30
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

BASE = "https://www.jstage.jst.go.jp"
ROOT = Path(__file__).resolve().parents[1]


def build_search_url(query: str, page: int = 1) -> str:
    """Build J-STAGE search URL."""
    params = {
        "textSearch": query,
        "page": page,
        "searchType": 0,  # all fields
    }
    return f"{BASE}/result/global/-char/ja?{urlencode(params)}"


def parse_article_links(html: str) -> list[dict]:
    """Parse article list from J-STAGE search result HTML."""
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for item in soup.select(".list_item"):
        title_a = item.select_one(".list_item_title a")
        if not title_a:
            continue
        title = title_a.get_text(strip=True)
        href = title_a.get("href", "")
        # Authors
        authors = ""
        author_el = item.select_one(".list_item_authors")
        if author_el:
            authors = author_el.get_text(strip=True)
        # Journal
        journal = ""
        journal_el = item.select_one(".list_item_journal")
        if journal_el:
            journal = journal_el.get_text(strip=True)
        # Date / Year
        year = ""
        year_el = item.select_one(".list_item_year")
        if year_el:
            year = year_el.get_text(strip=True)
        results.append({
            "title": title,
            "authors": authors,
            "journal": journal,
            "year": year,
            "url": href if href.startswith("http") else BASE + href,
        })
    return results


def fetch_article_detail(url: str) -> dict:
    """Fetch article abstract and keywords from detail page."""
    try:
        r = requests.get(url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        r.raise_for_status()
    except requests.RequestException as e:
        return {"abstract": "", "keywords": [], "error": str(e)}

    soup = BeautifulSoup(r.text, "html.parser")
    abstract = ""
    abs_el = soup.select_one(".global_article_abstract, .abstract_text")
    if abs_el:
        abstract = abs_el.get_text(strip=True)

    keywords = []
    for kw_el in soup.select(".global_article_keyword, .keyword_text"):
        kw = kw_el.get_text(strip=True)
        if kw:
            keywords.append(kw)

    # Try to find PDF link
    pdf_link = ""
    for a in soup.select("a"):
        href = a.get("href", "")
        if "/_pdf/" in href or href.endswith(".pdf"):
            pdf_link = href if href.startswith("http") else BASE + href
            break

    return {
        "abstract": abstract,
        "keywords": keywords,
        "pdf_link": pdf_link,
    }


def search_jstage(query: str, max_results: int = 20) -> list[dict]:
    """Search J-STAGE and return enriched results."""
    all_results = []
    page = 1
    while len(all_results) < max_results:
        url = build_search_url(query, page=page)
        print(f"[jstage] fetching page {page}: {url[:100]}...")
        try:
            r = requests.get(url, timeout=20, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"[error] {e}")
            break

        results = parse_article_links(r.text)
        if not results:
            break

        # Enrich with abstracts
        for res in results:
            if len(all_results) >= max_results:
                break
            detail = fetch_article_detail(res["url"])
            res.update(detail)
            all_results.append(res)
            time.sleep(0.5)  # be polite

        page += 1
        time.sleep(1)

    return all_results


def build_legal_queries() -> list[str]:
    """Return comprehensive list of legal/crime search queries."""
    return [
        # Violence / DV
        "配偶者暴力 被害者 支援",
        "DV 被害者 相談",
        "domestic violence victim support Japan",
        "虐待 子ども 相談",
        # Sexual violence
        "性暴力 被害者 支援",
        "性犯罪 同意 判例",
        "不同意性交 刑法 改正",
        "sexual assault victim Japan",
        # Fraud / consumer
        "消費者被害 詐欺 高齢者",
        "特殊詐欺 被害者 支援",
        # Workplace
        "職場 パワーハラスメント 被害者",
        "労働被害 相談",
        # Stalking / cyber
        "ストーカー 被害者 規制",
        "サイバー犯罪 被害者 支援",
        "ネットいじめ 被害者",
        # Drug / organized
        "薬物被害 依存 支援",
        # Hate crime / discrimination
        "ヘイトクライム 被害者",
        "差別 被害者 支援",
        # General victimology
        "被害者学 支援",
        "victimology Japan",
        "犯罪被害者 権利 支援",
        # Court / precedent analysis
        "判例 被害者 保護命令",
        "判例 DV 離婚",
        "判例 性犯罪 量刑",
    ]


def run_batch_search(output_path: Path, max_per_query: int = 15) -> None:
    """Run all legal queries and save merged results."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    all_papers = []
    seen_urls = set()

    for q in build_legal_queries():
        print(f"\n{'='*60}")
        print(f"Query: {q}")
        print(f"{'='*60}")
        results = search_jstage(q, max_results=max_per_query)
        for r in results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                all_papers.append(r)
        print(f"Got {len(results)} new, total unique {len(all_papers)}")
        time.sleep(2)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_papers, f, ensure_ascii=False, indent=2)

    print(f"\n[ok] Saved {len(all_papers)} papers to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="J-STAGE Legal Paper Crawler")
    parser.add_argument("--query", default="配偶者暴力 被害者 支援", help="Search query")
    parser.add_argument("--max", type=int, default=20, help="Max results per query")
    parser.add_argument("--batch", action="store_true", help="Run batch mode with all queries")
    parser.add_argument("--output", default=str(ROOT / "knowledge" / "seeds" / "jstage_legal_papers.json"), type=Path)
    args = parser.parse_args()

    if args.batch:
        run_batch_search(args.output, max_per_query=args.max)
    else:
        results = search_jstage(args.query, max_results=args.max)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"[ok] Saved {len(results)} results to {args.output}")


if __name__ == "__main__":
    main()
