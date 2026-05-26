"""Ingest 法テラス (日本司法支援センター) 全国事務所一覧.

The official CSV is published at https://www.houterasu.or.jp/ but the
exact URL changes occasionally. We let the operator pass --csv to override.

CSV expected columns (Japanese, varies by release):
  事務所名, 郵便番号, 住所, 電話番号, FAX, 受付時間, 緯度, 経度

If 緯度/経度 are missing we skip the row (geocoding is out of scope of MVP).
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from pathlib import Path

from sqlalchemy import text

from ingest.common import (
    PROCESSED_DIR,
    RAW_DIR,
    finish_run,
    logger,
    session_scope,
    start_run,
)

DATASET = "houterasu"

PREF_NAME_TO_CODE = {
    "北海道": "01", "青森県": "02", "岩手県": "03", "宮城県": "04", "秋田県": "05",
    "山形県": "06", "福島県": "07", "茨城県": "08", "栃木県": "09", "群馬県": "10",
    "埼玉県": "11", "千葉県": "12", "東京都": "13", "神奈川県": "14", "新潟県": "15",
    "富山県": "16", "石川県": "17", "福井県": "18", "山梨県": "19", "長野県": "20",
    "岐阜県": "21", "静岡県": "22", "愛知県": "23", "三重県": "24", "滋賀県": "25",
    "京都府": "26", "大阪府": "27", "兵庫県": "28", "奈良県": "29", "和歌山県": "30",
    "鳥取県": "31", "島根県": "32", "岡山県": "33", "広島県": "34", "山口県": "35",
    "徳島県": "36", "香川県": "37", "愛媛県": "38", "高知県": "39", "福岡県": "40",
    "佐賀県": "41", "長崎県": "42", "熊本県": "43", "大分県": "44", "宮崎県": "45",
    "鹿児島県": "46", "沖縄県": "47",
}


def _prefecture_code(address: str) -> str | None:
    for name, code in PREF_NAME_TO_CODE.items():
        if address.startswith(name):
            return code
    return None


async def run(csv_path: Path) -> None:
    async with session_scope() as s:
        run_id = await start_run(s, DATASET)
        rows_in = rows_out = 0
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows_in += 1
                    name = (row.get("事務所名") or row.get("name") or "").strip()
                    addr = (row.get("住所") or row.get("address") or "").strip()
                    lat = row.get("緯度") or row.get("lat")
                    lng = row.get("経度") or row.get("lng")
                    if not (name and lat and lng):
                        continue
                    try:
                        flat, flng = float(lat), float(lng)
                    except ValueError:
                        continue
                    pcode = _prefecture_code(addr) if addr else None
                    contact = {
                        "phone": (row.get("電話番号") or "").strip(),
                        "fax":   (row.get("FAX") or "").strip(),
                        "hours": (row.get("受付時間") or "").strip(),
                    }
                    await s.execute(
                        text(
                            """
                            INSERT INTO legalshield.support_org
                              (org_type, name, prefecture_code, address, geom,
                               services, contact, source, source_url, source_id, last_synced)
                            VALUES
                              ('law_terrace', :name, :pc, :addr,
                               ST_GeogFromText(:wkt),
                               ARRAY['legal_aid','general_consultation']::text[],
                               CAST(:contact AS jsonb),
                               'houterasu',
                               'https://www.houterasu.or.jp/',
                               :sid,
                               NOW())
                            ON CONFLICT (source, source_id) DO UPDATE SET
                               name = EXCLUDED.name,
                               address = EXCLUDED.address,
                               geom    = EXCLUDED.geom,
                               contact = EXCLUDED.contact,
                               last_synced = NOW()
                            """
                        ),
                        {
                            "name": name,
                            "pc": pcode,
                            "addr": addr,
                            "wkt": f"POINT({flng} {flat})",
                            "contact": _to_json(contact),
                            "sid": f"{name}|{addr}"[:200],
                        },
                    )
                    rows_out += 1
            await finish_run(s, run_id, "success", rows_in=rows_in, rows_out=rows_out)
            logger.info("houterasu ingest done: in=%d out=%d", rows_in, rows_out)
        except Exception as exc:
            await finish_run(s, run_id, "failed", rows_in=rows_in, rows_out=rows_out,
                              notes=repr(exc))
            raise


def _to_json(d: dict) -> str:
    import json
    return json.dumps(d, ensure_ascii=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True,
                     help="Path to 法テラス CSV (download manually from houterasu.or.jp)")
    args = ap.parse_args()
    if not args.csv.exists():
        print(f"CSV not found: {args.csv}", file=sys.stderr)
        return 2
    asyncio.run(run(args.csv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
