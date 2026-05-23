"""
裁判所公式書式集 爬蟲 (Japanese Courts Official Forms Crawler)
================================================================

裁判所 (https://www.courts.go.jp/saiban/syosiki/) で公開されている
12 カテゴリの公式書式（訴状・答弁書・準備書面・申立書 等）を網羅収集。

カテゴリ:
  1. 民事訴訟で使う書式            (一般民事 — 訴状・答弁書・準備書面等)
  2. 民事訴訟（交通事件）で使う書式 (交通事故専用)
  3. 少額訴訟で使う書式            (60 万円以下の少額)
  4. 民事調停で使う書式            (調停申立書 — 仲裁センターでも準用)
  5. 支払督促で使う書式
  6. 民事執行手続で使う書式
  7. 破産・再生手続で使う書式
  8. 労働審判で使う書式
  9. 家事審判で使う書式
 10. 家事調停で使う書式
 11. 人事訴訟で使う書式
 12. その他書式

Mapry 案件（仲裁中）にとって最重要:
  → カテゴリ 1 (民事訴訟) と カテゴリ 4 (民事調停)

法的配慮:
  - 裁判所公式書式は公衆送信目的で公開された行政情報
  - 著作権法 13 条により国・地方公共団体の告示等は権利の目的とならない
  - 私的・学術・公益研究目的での収集・分析・RAG 利用は完全に合法

使い方:
  python -m legalshield.crawlers.litigation_docs.courts_jp_forms
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import duckdb
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE = "https://www.courts.go.jp"
HUB_URL = f"{BASE}/saiban/syosiki/index.html"
USER_AGENT = (
    "Mozilla/5.0 (compatible; LegalShield-Research/1.0; "
    "+academic research; contact: kenji@hiiforest.com)"
)
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "ja,en;q=0.8"}
REQUEST_DELAY_SEC = 1.5

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "legalshield" / "knowledge" / "raw" / "litigation_docs" / "courts_jp_forms"
DOWNLOAD_DIR = RAW_DIR / "downloads"
HTML_DIR = RAW_DIR / "html"
DB_PATH = REPO_ROOT / "legalshield" / "lancedb" / "litigation.duckdb"
for d in (DOWNLOAD_DIR, HTML_DIR, DB_PATH.parent):
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("courts_jp_forms")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class CourtForm:
    form_id: str  # synthetic ID: category_slug__filename_stem
    category: str  # 民事訴訟 / 民事調停 / 少額訴訟 / ...
    category_slug: str
    title: str
    source_page_url: str
    file_url: str
    file_ext: str  # pdf / docx / doc / xls
    local_path: str
    sha256: str
    file_size: int
    description: str = ""
    fetched_at: str = ""


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, max=30))
def _get(url: str) -> requests.Response:
    log.debug("GET %s", url)
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    if r.encoding is None or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding or "utf-8"
    return r


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, max=30))
def _download(url: str, dest: Path) -> int:
    log.debug("DL  %s -> %s", url, dest)
    with requests.get(url, headers=HEADERS, timeout=120, stream=True) as r:
        r.raise_for_status()
        total = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total += len(chunk)
    return total


def _sleep() -> None:
    time.sleep(REQUEST_DELAY_SEC)


def _file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
def list_categories() -> list[tuple[str, str, str]]:
    """Return list of (category_name, category_slug, url)."""
    r = _get(HUB_URL)
    soup = BeautifulSoup(r.text, "lxml")
    cats: list[tuple[str, str, str]] = []
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if "syosiki_" not in h:
            continue
        url = urljoin(HUB_URL, h)
        slug_match = re.search(r"syosiki_([a-z_]+)", h)
        if not slug_match:
            continue
        slug = slug_match.group(1)
        name = a.get_text(strip=True)
        if not name:
            continue
        cats.append((name, slug, url))
    # dedupe preserving order
    seen = set()
    uniq = []
    for c in cats:
        if c[1] not in seen:
            seen.add(c[1])
            uniq.append(c)
    return uniq


_DOC_EXTS = (".pdf", ".docx", ".doc", ".xlsx", ".xls", ".rtf")


def list_forms_in_category(category_name: str, slug: str, page_url: str) -> list[CourtForm]:
    """Visit category page, optionally recurse into sub-index pages, collect all form documents."""
    forms: list[CourtForm] = []

    visited: set[str] = set()
    queue: list[str] = [page_url]

    while queue:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        try:
            r = _get(url)
        except Exception as e:
            log.warning("  cat=%s page fetch failed: %s", slug, e)
            continue

        # Save the HTML index for traceability
        page_id = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
        (HTML_DIR / f"{slug}__{page_id}.html").write_text(r.text, encoding="utf-8")

        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.find_all("a", href=True):
            h = a["href"]
            link_url = urljoin(url, h)
            txt = a.get_text(strip=True)
            lower = link_url.lower()
            # Recurse into syosiki sub-pages of same category
            if (
                f"syosiki_{slug}" in link_url
                and link_url.endswith(".html")
                and link_url not in visited
                and link_url.startswith(BASE)
            ):
                queue.append(link_url)
                continue
            # File downloads
            if any(lower.endswith(ext) for ext in _DOC_EXTS):
                ext = "." + lower.rsplit(".", 1)[-1]
                # Build local filename
                stem = Path(link_url).stem
                local_name = f"{slug}__{stem}{ext}"
                local_path = DOWNLOAD_DIR / local_name
                if local_path.exists() and local_path.stat().st_size > 0:
                    size = local_path.stat().st_size
                    sha = _file_sha256(local_path)
                else:
                    try:
                        size = _download(link_url, local_path)
                        sha = _file_sha256(local_path)
                        _sleep()
                    except Exception as e:
                        log.warning("  download fail %s: %s", link_url, e)
                        continue
                form = CourtForm(
                    form_id=f"{slug}__{stem}",
                    category=category_name,
                    category_slug=slug,
                    title=txt or stem,
                    source_page_url=url,
                    file_url=link_url,
                    file_ext=ext.lstrip("."),
                    local_path=str(local_path.relative_to(REPO_ROOT)),
                    sha256=sha,
                    file_size=size,
                    fetched_at=_now_iso(),
                )
                forms.append(form)
        _sleep()
    return forms


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
DDL = """
CREATE TABLE IF NOT EXISTS court_forms (
    form_id          VARCHAR PRIMARY KEY,
    category         VARCHAR,
    category_slug    VARCHAR,
    title            VARCHAR,
    source_page_url  VARCHAR,
    file_url         VARCHAR,
    file_ext         VARCHAR,
    local_path       VARCHAR,
    sha256           VARCHAR,
    file_size        BIGINT,
    description      TEXT,
    fetched_at       VARCHAR
);
"""


def upsert(con: duckdb.DuckDBPyConnection, f: CourtForm) -> None:
    con.execute("DELETE FROM court_forms WHERE form_id = ?", [f.form_id])
    con.execute(
        "INSERT INTO court_forms VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            f.form_id, f.category, f.category_slug, f.title, f.source_page_url,
            f.file_url, f.file_ext, f.local_path, f.sha256, f.file_size,
            f.description, f.fetched_at,
        ],
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
PRIORITY_SLUGS = (
    "minzi_sosyou",   # 民事訴訟（最重要 — 訴状・答弁書・準備書面）
    "minzi_tyoutei",  # 民事調停（仲裁にも準用される）
    "syogaku_sosyou", # 少額訴訟
    "roudou",         # 労働審判
)


def run(slug_filter: Optional[tuple[str, ...]] = None) -> dict:
    log.info("============================================================")
    log.info("Courts.go.jp Forms Crawler — start (DB: %s)", DB_PATH)
    log.info("============================================================")

    cats = list_categories()
    log.info("Discovered %d categories.", len(cats))
    for name, slug, url in cats:
        log.info("  · %s [%s]", name, slug)

    if slug_filter:
        cats = [c for c in cats if c[1] in slug_filter]
        log.info("Filter: keeping %d categories: %s", len(cats), slug_filter)

    con = duckdb.connect(str(DB_PATH))
    con.execute(DDL)

    grand_total = 0
    for i, (name, slug, url) in enumerate(cats, 1):
        log.info("[%d/%d] %s (%s)", i, len(cats), name, slug)
        forms = list_forms_in_category(name, slug, url)
        log.info("    → %d forms collected", len(forms))
        for f in forms:
            try:
                upsert(con, f)
                grand_total += 1
            except Exception as e:
                log.error("    upsert fail %s: %s", f.form_id, e)

    con.close()
    summary = {
        "categories_scanned": len(cats),
        "forms_total": grand_total,
        "download_dir": str(DOWNLOAD_DIR),
        "db": str(DB_PATH),
    }
    log.info("Done: %s", summary)
    return summary


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "priority":
        run(slug_filter=PRIORITY_SLUGS)
    elif len(sys.argv) > 1 and sys.argv[1] == "all":
        run()
    else:
        # Default: priority categories only (relevant to Mapry case)
        run(slug_filter=PRIORITY_SLUGS)
