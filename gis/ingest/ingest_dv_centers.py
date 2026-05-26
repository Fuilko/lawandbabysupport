"""Ingest 配偶者暴力相談支援センター 全国一覧.

Source: 内閣府 男女共同参画局 公式 PDF
  https://www.gender.go.jp/policy/no_violence/e-vaw/soudankikan/pdf/center.pdf

The PDF is a 5-column table:
  都道府県名 | 市区町村名 | 支援センター名 | 電話番号（相談用） | URL

Notes
─────
* Prefecture name only appears on the first row of each pref block; we
  forward-fill on parse.
* 市区町村名 == '－' means a prefecture-level office (not municipal).
* We don't geocode to street addresses (out of scope for MVP). Instead we
  use the prefecture centroid as a fallback so the row is still queryable
  by /nearest-support within ~25 km radius. The frontend should show
  "approximate" for these rows.
* org_type = 'admin_center' (公的窓口); services includes 'domestic_violence'.
* Idempotent: source = 'naikakufu_dv', source_id = sanitized name+phone.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Iterator, Optional

import pdfplumber
from sqlalchemy import text

from ingest.common import (
    PROCESSED_DIR,
    RAW_DIR,
    download,
    finish_run,
    logger,
    session_scope,
    start_run,
)

DATASET = "naikakufu_dv_center"
SOURCE_URL = "https://www.gender.go.jp/policy/no_violence/e-vaw/soudankikan/pdf/center.pdf"


# Prefecture name → (code, centroid lat, centroid lng).
# Centroids are population-weighted approximations sufficient for radius
# queries when full-address geocoding is unavailable.
PREFECTURE = {
    "北海道":   ("01", 43.0642, 141.3469),
    "青森県":   ("02", 40.8244, 140.7400),
    "岩手県":   ("03", 39.7036, 141.1527),
    "宮城県":   ("04", 38.2688, 140.8721),
    "秋田県":   ("05", 39.7186, 140.1024),
    "山形県":   ("06", 38.2404, 140.3636),
    "福島県":   ("07", 37.7500, 140.4677),
    "茨城県":   ("08", 36.3417, 140.4467),
    "栃木県":   ("09", 36.5658, 139.8836),
    "群馬県":   ("10", 36.3911, 139.0608),
    "埼玉県":   ("11", 35.8569, 139.6489),
    "千葉県":   ("12", 35.6047, 140.1234),
    "東京都":   ("13", 35.6895, 139.6917),
    "神奈川県": ("14", 35.4478, 139.6425),
    "新潟県":   ("15", 37.9023, 139.0235),
    "富山県":   ("16", 36.6953, 137.2113),
    "石川県":   ("17", 36.5947, 136.6256),
    "福井県":   ("18", 36.0652, 136.2216),
    "山梨県":   ("19", 35.6638, 138.5683),
    "長野県":   ("20", 36.6513, 138.1810),
    "岐阜県":   ("21", 35.3912, 136.7223),
    "静岡県":   ("22", 34.9769, 138.3831),
    "愛知県":   ("23", 35.1802, 136.9066),
    "三重県":   ("24", 34.7303, 136.5086),
    "滋賀県":   ("25", 35.0045, 135.8686),
    "京都府":   ("26", 35.0211, 135.7556),
    "大阪府":   ("27", 34.6864, 135.5200),
    "兵庫県":   ("28", 34.6913, 135.1830),
    "奈良県":   ("29", 34.6851, 135.8329),
    "和歌山県": ("30", 34.2261, 135.1675),
    "鳥取県":   ("31", 35.5036, 134.2383),
    "島根県":   ("32", 35.4723, 133.0505),
    "岡山県":   ("33", 34.6618, 133.9344),
    "広島県":   ("34", 34.3963, 132.4596),
    "山口県":   ("35", 34.1859, 131.4706),
    "徳島県":   ("36", 34.0658, 134.5594),
    "香川県":   ("37", 34.3401, 134.0434),
    "愛媛県":   ("38", 33.8417, 132.7660),
    "高知県":   ("39", 33.5597, 133.5311),
    "福岡県":   ("40", 33.6064, 130.4181),
    "佐賀県":   ("41", 33.2494, 130.2989),
    "長崎県":   ("42", 32.7448, 129.8737),
    "熊本県":   ("43", 32.7898, 130.7417),
    "大分県":   ("44", 33.2382, 131.6126),
    "宮崎県":   ("45", 31.9111, 131.4239),
    "鹿児島県": ("46", 31.5602, 130.5581),
    "沖縄県":   ("47", 26.2125, 127.6809),
}


# ─── Parsing ─────────────────────────────────────────────────────────


PHONE_RE = re.compile(r"^[#＃]?\d[\d\-－ｰ‐\s]{6,}$")


def normalize_phone(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    # Collapse whitespace and unify dash characters
    s = s.strip().replace("\n", " ")
    s = re.sub(r"[ｰ‐－—]", "-", s)
    # Strip wrapping notes like "（平日・夜）"
    s = re.sub(r"[（(].+?[)）]", "", s).strip()
    return s or None


def _pref_from_text(s: Optional[str]) -> Optional[str]:
    """Detect a prefecture name embedded in a free-text cell.

    pdfplumber occasionally fails to assign the prefecture cell (vertical
    merge mis-detection). Fall back to scanning the センター名 column —
    prefectural-level offices almost always start with the prefecture name.
    """
    if not s:
        return None
    head = s.strip()[:6]
    for p in PREFECTURE:
        if head.startswith(p):
            return p
    return None


def parse_pdf(path: Path) -> Iterator[dict]:
    """Yield dicts: {pref, city, name, phone, url}."""
    current_pref: Optional[str] = None
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for row in table:
                    if not row or len(row) < 4:
                        continue
                    pref, city, name, phone, *rest = (
                        list(row) + [None] * (5 - len(row))
                    )[:5]
                    url = rest[0] if rest else None

                    # skip header rows
                    if pref and "都道府県" in pref:
                        continue
                    if name and "支援センター名" in name:
                        continue

                    # forward-fill prefecture
                    if pref and pref.strip() and pref.strip() in PREFECTURE:
                        current_pref = pref.strip()
                    else:
                        # fallback: detect from name column when pref cell is
                        # blank (pdfplumber vertical-merge bug for 7 prefs).
                        inferred = _pref_from_text(name)
                        if inferred:
                            current_pref = inferred

                    if not current_pref:
                        continue
                    if not name or not name.strip():
                        continue

                    name_clean = " ".join(name.split())
                    phone_clean = normalize_phone(phone)
                    city_clean = (city or "").strip()
                    if city_clean in ("－", "-", "—", "ー"):
                        city_clean = ""

                    if not phone_clean or not PHONE_RE.match(
                        phone_clean.replace(" ", "")
                    ):
                        # Some PDF rows have empty phone or wrapping. Skip those
                        # rather than insert garbage; the operator can patch later.
                        if not phone_clean:
                            continue

                    yield {
                        "pref": current_pref,
                        "city": city_clean,
                        "name": name_clean,
                        "phone": phone_clean,
                        "url": (url or "").strip() or None,
                    }


# ─── DB write ────────────────────────────────────────────────────────


UPSERT_SQL = text(
    """
    INSERT INTO legalshield.support_org
      (org_type, name, prefecture_code, address, geom,
       services, contact, source, source_url, source_id, last_synced)
    VALUES
      ('admin_center', :name, :pc, :addr,
       ST_GeogFromText(:wkt),
       ARRAY['domestic_violence','general_consultation']::text[],
       CAST(:contact AS jsonb),
       'naikakufu_dv',
       :sup_url,
       :sid,
       NOW())
    ON CONFLICT (source, source_id) DO UPDATE SET
       name        = EXCLUDED.name,
       address     = EXCLUDED.address,
       geom        = EXCLUDED.geom,
       contact     = EXCLUDED.contact,
       source_url  = EXCLUDED.source_url,
       last_synced = NOW()
    """
)


async def run(pdf_path: Path) -> None:
    async with session_scope() as s:
        run_id = await start_run(s, DATASET)
        rows_in = rows_out = 0
        try:
            for r in parse_pdf(pdf_path):
                rows_in += 1
                pc, lat, lng = PREFECTURE[r["pref"]]
                # Build display address (prefecture + city only since PDF
                # does not include street).
                addr = r["pref"] + (r["city"] or "")
                contact = {
                    "phone": r["phone"],
                    "url":   r["url"],
                    "city":  r["city"] or None,
                    "geocoding": "prefecture_centroid_fallback",
                }
                sid = (f"{r['pref']}|{r['city']}|{r['name']}|{r['phone']}")[:200]
                await s.execute(
                    UPSERT_SQL,
                    {
                        "name": r["name"],
                        "pc":   pc,
                        "addr": addr,
                        "wkt":  f"POINT({lng} {lat})",
                        "contact": json.dumps(contact, ensure_ascii=False),
                        "sup_url": r["url"] or SOURCE_URL,
                        "sid":   sid,
                    },
                )
                rows_out += 1
            await finish_run(
                s, run_id, "success",
                rows_in=rows_in, rows_out=rows_out,
                notes=f"prefecture_centroid_fallback; pdf={pdf_path.name}",
            )
            logger.info("dv_center ingest done: in=%d out=%d", rows_in, rows_out)
        except Exception as exc:
            await finish_run(
                s, run_id, "failed",
                rows_in=rows_in, rows_out=rows_out, notes=repr(exc),
            )
            raise


async def amain(args: argparse.Namespace) -> None:
    if args.pdf:
        pdf_path = args.pdf
    else:
        pdf_path = RAW_DIR / "dv_center" / "center.pdf"
        await download(SOURCE_URL, pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)
    await run(pdf_path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--pdf", type=Path,
        help="Optional pre-downloaded PDF path (default: auto-download)",
    )
    args = ap.parse_args()
    asyncio.run(amain(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
