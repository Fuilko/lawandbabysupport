"""
CALL4 公共訴訟プラットフォーム 爬蟲 (Public Interest Litigation Crawler)
======================================================================

CALL4 (https://www.call4.jp) は日本の公共訴訟（社会課題訴訟）特化型
クラウドファンディング・ストーリーテリングプラットフォーム。

このモジュールは:
  1. 全公開ケース ID を search.php から列挙
  2. 各ケース詳細を info.php?type=items&id=IXXXXXXX から取得
  3. メタデータ・本文・関連 PDF を抽出
  4. 原始 HTML を raw/litigation_docs/call4/html/ に保存
  5. 構造化済データを DuckDB (litigation.duckdb) に投入

法的・倫理的配慮:
  - robots.txt 確認済（CALL4 は robots.txt なし、明示的禁止なし）
  - 1.5 秒/リクエスト の rate limiting
  - User-Agent に研究目的を明示
  - PDF の再配布は行わず、内部 RAG 学習用途のみ
  - CALL4 ToS に基づく学術研究フェアユース範囲内

使い方:
  python -m legalshield.crawlers.litigation_docs.call4_scraper
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import duckdb
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL = "https://www.call4.jp"
SEARCH_URL = f"{BASE_URL}/search.php?type=items&run=true&sort=number&sort_PAL=desc&page={{page}}"
CASE_URL = f"{BASE_URL}/info.php?type=items&id={{case_id}}"
ACTION_URL = f"{BASE_URL}/search.php?type=action&run=true&page={{page}}"  # 期日 calendar

USER_AGENT = (
    "Mozilla/5.0 (compatible; LegalShield-Research/1.0; "
    "+academic research; contact: kenji@hiiforest.com)"
)
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "ja,en;q=0.8"}

REQUEST_DELAY_SEC = 1.5  # be polite
PAGE_SCAN_LIMIT = 50  # safety bound; auto-stops when no new IDs

# Workspace paths
REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "legalshield" / "knowledge" / "raw" / "litigation_docs" / "call4"
HTML_DIR = RAW_DIR / "html"
PDF_DIR = RAW_DIR / "pdfs"
DB_PATH = REPO_ROOT / "legalshield" / "lancedb" / "litigation.duckdb"

for d in (HTML_DIR, PDF_DIR, DB_PATH.parent):
    d.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("call4_scraper")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class Call4Case:
    """Structured CALL4 case record."""

    case_id: str  # e.g. I0000031
    url: str
    title_ja: str = ""
    title_en: str = ""
    description_ja: str = ""
    description_en: str = ""
    court: str = ""
    plaintiff_count: Optional[int] = None
    damages_claim: str = ""  # 賠償請求額
    legal_team: str = ""
    legal_team_size: Optional[int] = None
    status: str = ""
    filed_at: str = ""  # ISO date
    last_seen: str = ""
    raw_html_sha256: str = ""
    related_pdfs: list[str] = field(default_factory=list)
    related_story_ids: list[str] = field(default_factory=list)
    related_column_ids: list[str] = field(default_factory=list)
    fetched_at: str = ""
    full_text: str = ""  # cleaned plaintext for embedding


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, max=30))
def _get(url: str) -> requests.Response:
    log.debug("GET %s", url)
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r


def _sleep() -> None:
    time.sleep(REQUEST_DELAY_SEC)


# ---------------------------------------------------------------------------
# Step 1: Enumerate case IDs
# ---------------------------------------------------------------------------
def enumerate_case_ids(max_pages: int = PAGE_SCAN_LIMIT) -> list[str]:
    """Walk paginated search and return all unique case IDs (sorted)."""
    seen: set[str] = set()
    stable = 0
    for page in range(1, max_pages + 1):
        try:
            r = _get(SEARCH_URL.format(page=page))
        except Exception as e:
            log.warning("page=%d fetch failed: %s", page, e)
            break
        ids = set(re.findall(r"id=(I\d{7})", r.text))
        new = ids - seen
        seen.update(ids)
        log.info(
            "  list page=%d → found %d ids (new %d, total %d)",
            page, len(ids), len(new), len(seen),
        )
        if not new:
            stable += 1
            if stable >= 3:
                log.info("No new IDs for 3 consecutive pages, stopping.")
                break
        else:
            stable = 0
        _sleep()
    return sorted(seen)


# ---------------------------------------------------------------------------
# Step 2: Parse individual case page
# ---------------------------------------------------------------------------
_RE_INT = re.compile(r"(\d[\d,]*)")


def _maybe_int(text: str) -> Optional[int]:
    m = _RE_INT.search(text or "")
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


def parse_case_page(case_id: str, html: str, url: str) -> Call4Case:
    soup = BeautifulSoup(html, "lxml")
    case = Call4Case(case_id=case_id, url=url)
    case.fetched_at = _now_iso()
    case.raw_html_sha256 = hashlib.sha256(html.encode("utf-8")).hexdigest()

    # Title from og:title or first h2
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        case.title_ja = og_title["content"].strip()
    else:
        h2 = soup.find(["h1", "h2"])
        if h2:
            case.title_ja = h2.get_text(strip=True)

    # Description from og:description
    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        case.description_ja = og_desc["content"].strip()

    # Full text (visible paragraphs)
    text_blocks: list[str] = []
    for tag in soup.find_all(["p", "h2", "h3", "h4", "li"]):
        txt = tag.get_text(" ", strip=True)
        if not txt:
            continue
        if any(skip in txt.lower() for skip in ("cookie", "privacy", "©", "copyright")):
            continue
        text_blocks.append(txt)
    case.full_text = "\n".join(text_blocks)

    # Heuristic field extraction from full text
    for line in text_blocks:
        if "原告" in line and case.plaintiff_count is None:
            n = _maybe_int(line)
            if n and 1 <= n <= 5000:
                case.plaintiff_count = n
        if "弁護士" in line and ("名" in line or "人" in line) and case.legal_team_size is None:
            n = _maybe_int(line)
            if n and 1 <= n <= 500:
                case.legal_team_size = n
        if "賠償" in line and not case.damages_claim:
            case.damages_claim = line[:200]
        if any(c in line for c in ("地方裁判所", "高等裁判所", "最高裁判所")) and not case.court:
            case.court = line[:120]

    # Related links: stories / columns
    for a in soup.find_all("a", href=True):
        h = a["href"]
        m = re.search(r"/story/\?p=(\d+)", h)
        if m:
            case.related_story_ids.append(m.group(1))
        m = re.search(r"/column/\?p=(\d+)", h)
        if m:
            case.related_column_ids.append(m.group(1))
        if h.lower().endswith(".pdf") and "Privacy" not in h and "Cookie" not in h:
            case.related_pdfs.append(h)
    case.related_story_ids = sorted(set(case.related_story_ids))
    case.related_column_ids = sorted(set(case.related_column_ids))
    case.related_pdfs = sorted(set(case.related_pdfs))

    return case


def fetch_case(case_id: str) -> Optional[Call4Case]:
    url = CASE_URL.format(case_id=case_id)
    try:
        r = _get(url)
    except Exception as e:
        log.error("Failed to fetch %s: %s", case_id, e)
        return None

    # Persist raw HTML
    html_path = HTML_DIR / f"{case_id}.html"
    html_path.write_text(r.text, encoding="utf-8")

    case = parse_case_page(case_id, r.text, url)
    case.last_seen = _now_iso()
    return case


# ---------------------------------------------------------------------------
# Step 3: Persist to DuckDB
# ---------------------------------------------------------------------------
DDL = """
CREATE TABLE IF NOT EXISTS call4_cases (
    case_id              VARCHAR PRIMARY KEY,
    url                  VARCHAR,
    title_ja             VARCHAR,
    title_en             VARCHAR,
    description_ja       TEXT,
    description_en       TEXT,
    court                VARCHAR,
    plaintiff_count      INTEGER,
    damages_claim        VARCHAR,
    legal_team           VARCHAR,
    legal_team_size      INTEGER,
    status               VARCHAR,
    filed_at             VARCHAR,
    last_seen            VARCHAR,
    raw_html_sha256      VARCHAR,
    related_pdfs         VARCHAR[],
    related_story_ids    VARCHAR[],
    related_column_ids   VARCHAR[],
    fetched_at           VARCHAR,
    full_text            TEXT
);
"""


def upsert_case(con: duckdb.DuckDBPyConnection, case: Call4Case) -> None:
    con.execute("DELETE FROM call4_cases WHERE case_id = ?", [case.case_id])
    con.execute(
        """
        INSERT INTO call4_cases VALUES (
          ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        )
        """,
        [
            case.case_id, case.url, case.title_ja, case.title_en,
            case.description_ja, case.description_en, case.court,
            case.plaintiff_count, case.damages_claim, case.legal_team,
            case.legal_team_size, case.status, case.filed_at,
            case.last_seen, case.raw_html_sha256,
            case.related_pdfs, case.related_story_ids,
            case.related_column_ids, case.fetched_at, case.full_text,
        ],
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
def run(limit: Optional[int] = None) -> dict:
    """Full crawl. Pass limit to cap cases for testing."""
    log.info("============================================================")
    log.info("CALL4 Crawler — start  (DB: %s)", DB_PATH)
    log.info("============================================================")

    case_ids = enumerate_case_ids()
    log.info("Discovered %d unique cases.", len(case_ids))
    if limit:
        case_ids = case_ids[:limit]
        log.info("LIMIT applied: scraping first %d", limit)

    con = duckdb.connect(str(DB_PATH))
    con.execute(DDL)

    ok, fail = 0, 0
    for i, cid in enumerate(case_ids, 1):
        log.info("[%d/%d] %s", i, len(case_ids), cid)
        case = fetch_case(cid)
        if case is None:
            fail += 1
            _sleep()
            continue
        try:
            upsert_case(con, case)
            ok += 1
        except Exception as e:
            log.error("DB upsert failed for %s: %s", cid, e)
            fail += 1
        _sleep()

    con.close()
    summary = {
        "total_ids": len(case_ids),
        "ok": ok,
        "failed": fail,
        "db": str(DB_PATH),
        "raw_html_dir": str(HTML_DIR),
    }
    log.info("Done: %s", json.dumps(summary, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run(limit=limit)
