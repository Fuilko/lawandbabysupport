"""
Reference downloader.

Manifest (refs/manifest.py) の各 URL を docs/refs/{category}/{subcategory}/ に保存。
- PDF: そのまま .pdf
- HTML: .html (本文) + 内部の PDF/Excel リンクをサブディレクトリに自動取得
- HTML ランディングから 7 件以下の関連 PDF/Excel を best-effort で取得

成果物:
  docs/refs/manifest.json    各エントリの取得状況
  docs/refs/refs.bib         BibTeX
  docs/refs/INDEX.md         人間用一覧
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests

from legalshield.refs.manifest import REFS

logger = logging.getLogger("refs.download")

REFS_ROOT = Path(__file__).resolve().parents[2] / "docs" / "refs"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# HTML から関連 PDF/Excel を best-effort で抽出する設定
SUB_DOWNLOAD_PATTERNS = re.compile(
    r'href="([^"]+\.(?:pdf|xlsx|xls|csv|zip))"',
    re.IGNORECASE,
)
MAX_SUB_DOWNLOADS_PER_PAGE = 8


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
        "Accept-Language": "ja, zh-TW;q=0.9, en-US;q=0.8, en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Ch-Ua": '"Chromium";v="126", "Google Chrome";v="126"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    })
    return s


def _safe_filename(url: str, fallback: str) -> str:
    path = urlparse(url).path
    name = Path(path).name or fallback
    name = re.sub(r'[^A-Za-z0-9._\-]+', '_', name)
    if not name or name.startswith('.'):
        name = fallback
    return name[:200]


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _fetch(url: str, dest: Path, session: requests.Session, timeout: int = 90) -> dict:
    """単一 URL をダウンロード。成功なら {'ok': True, 'sha256': ..., 'size': ..., 'http': 200}。"""
    try:
        with session.get(url, stream=True, timeout=timeout, allow_redirects=True) as r:
            status = r.status_code
            ctype = r.headers.get("Content-Type", "")
            if status != 200:
                return {"ok": False, "http": status, "error": f"HTTP {status}", "url": url}
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("wb") as f:
                for chunk in r.iter_content(64 * 1024):
                    f.write(chunk)
        size = dest.stat().st_size
        if size == 0:
            dest.unlink(missing_ok=True)
            return {"ok": False, "http": status, "error": "empty body", "url": url}
        return {
            "ok": True,
            "http": status,
            "content_type": ctype,
            "size": size,
            "sha256": _sha256(dest),
            "url": url,
            "path": str(dest.relative_to(REFS_ROOT)),
        }
    except requests.RequestException as e:
        return {"ok": False, "error": str(e), "url": url}


def _extract_sub_links(html_path: Path, base_url: str) -> list[str]:
    """HTML 中から PDF/Excel/CSV へのリンクを抽出して絶対 URL に。"""
    try:
        text = html_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    rels = SUB_DOWNLOAD_PATTERNS.findall(text)
    out: list[str] = []
    seen: set[str] = set()
    for rel in rels:
        absu = urljoin(base_url, rel)
        if absu in seen:
            continue
        seen.add(absu)
        out.append(absu)
        if len(out) >= MAX_SUB_DOWNLOADS_PER_PAGE:
            break
    return out


def download_one(entry: dict, session: requests.Session, sleep_sec: float = 1.5) -> dict:
    """1 エントリを取得。HTML の場合は中の PDF/Excel も best-effort で取得。"""
    cat = entry["category"]
    sub = entry.get("subcategory", "misc")
    folder = REFS_ROOT / cat / sub
    folder.mkdir(parents=True, exist_ok=True)

    ext_map = {"pdf": ".pdf", "html": ".html", "xlsx": ".xlsx", "xls": ".xls", "csv": ".csv", "zip": ".zip"}
    fallback = f"{entry['key']}{ext_map.get(entry['kind'], '.bin')}"
    fname = _safe_filename(entry["url"], fallback)
    # ensure key prefix for sortability
    if not fname.startswith(entry["key"]):
        fname = f"{entry['key']}__{fname}"
    dest = folder / fname

    logger.info("[%s] -> %s", entry["key"], dest.relative_to(REFS_ROOT))
    result = _fetch(entry["url"], dest, session)
    result["key"] = entry["key"]
    result["title"] = entry["title"]
    result["kind"] = entry["kind"]
    result["category"] = cat
    result["subcategory"] = sub
    result["year"] = entry.get("year")
    result["publisher"] = entry.get("publisher")
    result["necessity_for"] = entry.get("necessity_for", [])
    result["fetched_at"] = datetime.now(timezone.utc).isoformat()

    sub_results: list[dict] = []
    if result.get("ok") and entry["kind"] == "html":
        # HTML ランディングなら中の PDF/Excel を漁る
        sub_urls = _extract_sub_links(dest, entry["url"])
        sub_folder = folder / f"{entry['key']}__assets"
        for sub_url in sub_urls:
            sub_name = _safe_filename(sub_url, "asset.bin")
            sub_dest = sub_folder / sub_name
            time.sleep(sleep_sec)
            r2 = _fetch(sub_url, sub_dest, session)
            r2["from_landing"] = entry["key"]
            sub_results.append(r2)
    if sub_results:
        result["sub_assets"] = sub_results

    time.sleep(sleep_sec)
    return result


def write_bibtex(results: list[dict], path: Path) -> None:
    lines: list[str] = []
    for entry in REFS:
        key = entry["key"]
        btype = entry.get("bibtex_type", "misc")
        title = entry["title"].replace("{", "").replace("}", "")
        publisher = entry.get("publisher", "")
        year = entry.get("year", "")
        url = entry["url"]
        notes = entry.get("notes", "")
        lines.append(f"@{btype}{{{key},")
        lines.append(f"  title        = {{{title}}},")
        if publisher:
            lines.append(f"  publisher    = {{{publisher}}},")
            lines.append(f"  organization = {{{publisher}}},")
        if year:
            lines.append(f"  year         = {{{year}}},")
        lines.append(f"  url          = {{{url}}},")
        lines.append(f"  urldate      = {{{datetime.now().date().isoformat()}}},")
        if notes:
            esc = notes.replace("{", "").replace("}", "")
            lines.append(f"  note         = {{{esc}}},")
        lines.append("}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_index_md(results: list[dict], path: Path) -> None:
    by_cat: dict[str, list[dict]] = {}
    for r in results:
        by_cat.setdefault(r.get("category", "misc"), []).append(r)
    lines = [
        "# Evidence References Index",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Total entries: {len(results)}",
        "",
        "Status legend: ✅ ok / ⚠️ HTTP fail / 🚫 paywall / 📎 landing-only",
        "",
    ]
    cat_titles = {
        "jp": "🇯🇵 日本政府統計・調査",
        "tw": "🇹🇼 台湾政府統計・報告",
        "academic": "📚 学術論文",
        "international": "🌐 国際 NPO・ガイドライン",
        "laws": "⚖️ 法規",
    }
    for cat in ["jp", "tw", "academic", "international", "laws"]:
        items = by_cat.get(cat, [])
        if not items:
            continue
        lines.append(f"## {cat_titles.get(cat, cat)}")
        lines.append("")
        lines.append("| Key | Title | Year | Status | Path |")
        lines.append("|-----|-------|------|--------|------|")
        for r in items:
            status = "✅" if r.get("ok") else f"⚠️ {r.get('http', '?')}"
            p = r.get("path", "-")
            need = ", ".join(r.get("necessity_for", []))
            lines.append(
                f"| `{r['key']}` | {r['title']} | {r.get('year','')} | {status} | `{p}` |"
            )
        lines.append("")
        # subasset リスト
        for r in items:
            subs = r.get("sub_assets", [])
            if subs:
                lines.append(f"<details><summary>Sub-assets from <code>{r['key']}</code> ({len(subs)})</summary>")
                lines.append("")
                for s in subs:
                    st = "✅" if s.get("ok") else f"⚠️ {s.get('http','?')}"
                    sp = s.get("path", "-")
                    su = s.get("url", "-")
                    lines.append(f"- {st} [{Path(su).name}]({su}) → `{sp}`")
                lines.append("")
                lines.append("</details>")
                lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--filter-category", default=None, help="jp|tw|academic|international|laws")
    parser.add_argument("--sleep", type=float, default=1.5)
    parser.add_argument("--retry-failed", action="store_true", help="既存 manifest.json の失敗のみ再試行")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    REFS_ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path = REFS_ROOT / "manifest.json"

    # 既存マニフェスト読み込み (差分実行のため)
    existing: dict[str, dict] = {}
    if manifest_path.exists():
        try:
            existing = {e["key"]: e for e in json.loads(manifest_path.read_text("utf-8"))}
        except json.JSONDecodeError:
            existing = {}

    targets = REFS
    if args.filter_category:
        targets = [r for r in REFS if r["category"] == args.filter_category]
    if args.retry_failed:
        targets = [r for r in targets if not (existing.get(r["key"], {}).get("ok"))]
        logger.info("retry-failed mode: %d targets", len(targets))

    session = _session()
    results: list[dict] = []
    # 既存の成功は維持
    for r in REFS:
        if r["key"] in existing and existing[r["key"]].get("ok") and r not in targets:
            results.append(existing[r["key"]])

    for entry in targets:
        try:
            r = download_one(entry, session, sleep_sec=args.sleep)
        except Exception as e:  # noqa: BLE001
            logger.exception("error on %s", entry["key"])
            r = {"key": entry["key"], "ok": False, "error": str(e), "url": entry["url"]}
        results.append(r)

    # キー重複除去 (既存と新規が両方ある場合は新規優先)
    dedup: dict[str, dict] = {}
    for r in results:
        dedup[r["key"]] = r
    results = list(dedup.values())

    manifest_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    write_bibtex(results, REFS_ROOT / "refs.bib")
    write_index_md(results, REFS_ROOT / "INDEX.md")

    ok = sum(1 for r in results if r.get("ok"))
    fail = sum(1 for r in results if not r.get("ok"))
    n_sub = sum(len(r.get("sub_assets", [])) for r in results)
    sub_ok = sum(1 for r in results for s in r.get("sub_assets", []) if s.get("ok"))
    logger.info("DONE: main %d/%d ok, sub-assets %d/%d ok",
                ok, ok + fail, sub_ok, n_sub)
    print(json.dumps(
        {"main_ok": ok, "main_fail": fail, "sub_total": n_sub, "sub_ok": sub_ok,
         "manifest": str(manifest_path),
         "index": str(REFS_ROOT / "INDEX.md"),
         "bibtex": str(REFS_ROOT / "refs.bib")},
        ensure_ascii=False, indent=2,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
