"""
警察庁 ストーカー・配偶者暴力 年次報告ハーベスタ

データソース:
  https://www.npa.go.jp/bureau/safetylife/stalker/
  毎年: R{n}_STDVRPCAkouhousiryou(_syuusei).pdf
  → ストーカー / 配偶者暴力 / リベンジポルノ / 児童虐待 等の
    相談件数・検挙件数・警告件数・禁止命令件数を含む

LegalShield での用途:
  「ギャップ係数」「沈黙率」「地域偏在係数」の計算根拠
  → JUDB (Japan Underreporting Database) へ流入

著作権: 著作権法13条 公的資料 (no copyright)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import requests

logger = logging.getLogger("npa_stalking")

BASE_URL = "https://www.npa.go.jp/bureau/safetylife/stalker"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "knowledge" / "raw" / "jp_underreporting" / "npa_stalking"

# 既知の URL パターン (令和年号)
# _syuusei (修正版) が出る年もあるため両方試行
KNOWN_URL_PATTERNS = [
    "R{reiwa}_STDVRPCAkouhousiryou_syuusei.pdf",
    "R{reiwa}_STDVRPCAkouhousiryou.pdf",
]

USER_AGENT = "LegalShieldResearchBot/0.1 (+contact: research@legalshield.example)"


@dataclass
class Report:
    reiwa_year: int          # 令和n年 (例: 5)
    fiscal_year: int         # 西暦 (例: 2023)
    url: str
    local_path: str
    sha256: str
    fetched_at: str
    bytes: int


def reiwa_to_western(reiwa: int) -> int:
    """令和n年 → 西暦"""
    return 2018 + reiwa  # 令和元年 = 2019


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_year(
    reiwa: int,
    out_dir: Path,
    session: Optional[requests.Session] = None,
    timeout: int = 120,
    sleep_sec: float = 2.0,
) -> Optional[Report]:
    """指定令和年の年次報告 PDF を取得。

    Returns None if not found (URL patterns exhausted).
    """
    session = session or _session()
    out_dir.mkdir(parents=True, exist_ok=True)
    for tmpl in KNOWN_URL_PATTERNS:
        fname = tmpl.format(reiwa=reiwa)
        url = f"{BASE_URL}/{fname}"
        local = out_dir / fname
        if local.exists() and local.stat().st_size > 1000:
            logger.info("cache hit: %s", local.name)
            return Report(
                reiwa_year=reiwa,
                fiscal_year=reiwa_to_western(reiwa),
                url=url,
                local_path=str(local),
                sha256=_sha256(local),
                fetched_at=datetime.now(timezone.utc).isoformat(),
                bytes=local.stat().st_size,
            )
        try:
            r = session.get(url, timeout=timeout, stream=True)
        except requests.RequestException as e:
            logger.warning("R%d %s: request error %s", reiwa, fname, e)
            time.sleep(sleep_sec)
            continue
        if r.status_code == 404:
            logger.debug("R%d %s: 404", reiwa, fname)
            continue
        if r.status_code != 200:
            logger.warning("R%d %s: HTTP %d", reiwa, fname, r.status_code)
            continue
        # save
        with local.open("wb") as f:
            for chunk in r.iter_content(1024 * 64):
                f.write(chunk)
        size = local.stat().st_size
        if size < 1000:
            logger.warning("R%d %s: too small (%d bytes), discarding", reiwa, fname, size)
            local.unlink(missing_ok=True)
            continue
        logger.info("R%d fetched: %s (%d bytes)", reiwa, fname, size)
        time.sleep(sleep_sec)
        return Report(
            reiwa_year=reiwa,
            fiscal_year=reiwa_to_western(reiwa),
            url=url,
            local_path=str(local),
            sha256=_sha256(local),
            fetched_at=datetime.now(timezone.utc).isoformat(),
            bytes=size,
        )
    return None


def extract_text(pdf_path: Path) -> str:
    """PDF から本文抽出 (pypdf を優先、無ければ pdfminer)。"""
    try:
        import pypdf  # type: ignore
        reader = pypdf.PdfReader(str(pdf_path))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except ImportError:
        try:
            from pdfminer.high_level import extract_text as pmt  # type: ignore
            return pmt(str(pdf_path))
        except ImportError as e:
            raise RuntimeError("pypdf or pdfminer.six required") from e


# 統計値抽出用パターン (主要指標のみ)
# PDF レイアウトに依存するため、確実に取れるものに絞る
STAT_PATTERNS = {
    "stalker_soudan":         r"ストーカー事案[^\n]*?相談[^\n]*?(\d{1,3}(?:[,，]\d{3})*)\s*件",
    "stalker_kenkyo":         r"ストーカー[^\n]*?検挙[^\n]*?(\d{1,3}(?:[,，]\d{3})*)\s*件",
    "stalker_keikoku":        r"ストーカー[^\n]*?警告[^\n]*?(\d{1,3}(?:[,，]\d{3})*)\s*件",
    "stalker_kinshi_meirei":  r"ストーカー[^\n]*?禁止命令[^\n]*?(\d{1,3}(?:[,，]\d{3})*)\s*件",
    "dv_soudan":              r"配偶者[^\n]*?暴力[^\n]*?相談[^\n]*?(\d{1,3}(?:[,，]\d{3})*)\s*件",
    "dv_kenkyo":              r"配偶者[^\n]*?暴力[^\n]*?検挙[^\n]*?(\d{1,3}(?:[,，]\d{3})*)\s*件",
}


def parse_statistics(text: str) -> dict[str, Optional[int]]:
    """テキストから主要統計値を抽出 (best-effort)。"""
    out: dict[str, Optional[int]] = {}
    for key, pat in STAT_PATTERNS.items():
        m = re.search(pat, text)
        if not m:
            out[key] = None
            continue
        num = m.group(1).replace(",", "").replace("，", "")
        try:
            out[key] = int(num)
        except ValueError:
            out[key] = None
    return out


def harvest(
    out_dir: Path = DEFAULT_OUT,
    reiwa_years: Optional[Iterable[int]] = None,
    sleep_sec: float = 2.0,
) -> dict:
    """指定年範囲の年次報告を取得し、統計値を JSONL に出力。

    Args:
        reiwa_years: 取得対象の令和年 (デフォルト: 1〜直近)
    """
    if reiwa_years is None:
        # 令和元年 (2019) 〜 現在
        current_western = datetime.now().year
        current_reiwa = current_western - 2018
        reiwa_years = range(1, current_reiwa + 1)
    reiwa_years = list(reiwa_years)

    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"stats_{ts}.jsonl"
    summary_path = out_dir / f"summary_{ts}.json"

    session = _session()
    reports: list[Report] = []
    rows: list[dict] = []

    with out_path.open("w", encoding="utf-8") as f:
        for reiwa in reiwa_years:
            rep = fetch_year(reiwa, out_dir, session=session, sleep_sec=sleep_sec)
            if not rep:
                logger.warning("R%d: no report found", reiwa)
                continue
            reports.append(rep)
            try:
                text = extract_text(Path(rep.local_path))
            except Exception as e:
                logger.error("R%d text extract failed: %s", reiwa, e)
                continue
            stats = parse_statistics(text)
            row = {
                "source": "npa.go.jp/bureau/safetylife/stalker",
                "category": "stalker_dv_annual_report",
                "reiwa_year": rep.reiwa_year,
                "fiscal_year": rep.fiscal_year,
                "url": rep.url,
                "sha256": rep.sha256,
                "fetched_at": rep.fetched_at,
                "stats": stats,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows.append(row)
            logger.info("R%d stats: %s", reiwa, {k: v for k, v in stats.items() if v is not None})

    summary = {
        "fetched_at": ts,
        "reports": [asdict(r) for r in reports],
        "rows_extracted": len(rows),
        "out_file": str(out_path),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("done: %d reports, %d rows", len(reports), len(rows))
    return summary


def _main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="警察庁 ストーカー・DV 年次報告ハーベスタ")
    parser.add_argument("--from-reiwa", type=int, default=1, help="開始令和年 (デフォルト 1)")
    parser.add_argument("--to-reiwa", type=int, default=None, help="終了令和年 (デフォルト: 現在)")
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    end = args.to_reiwa or (datetime.now().year - 2018)
    years = range(args.from_reiwa, end + 1)
    summary = harvest(out_dir=args.out, reiwa_years=years, sleep_sec=args.sleep)
    print(json.dumps(
        {k: v for k, v in summary.items() if k != "reports"},
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
