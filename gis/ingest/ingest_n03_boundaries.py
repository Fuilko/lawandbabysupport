"""Ingest 国土数値情報 N03 行政区域 (prefecture + city polygons).

Source: https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N03-v3_1.html
Download the latest year's nationwide ZIP (Shapefile, JGD2011), unzip,
then point this script at the .shp.

Operator usage:
  python -m ingest.ingest_n03_boundaries --shp /app/data/raw/N03/N03_*.shp
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# geopandas is heavy; import lazily so unit tests that don't touch this module
# stay fast.

from sqlalchemy import text

from ingest.common import finish_run, logger, session_scope, start_run

DATASET = "n03_boundaries"


async def run(shp_path: Path) -> None:
    import geopandas as gpd  # lazy
    from shapely.geometry import MultiPolygon

    logger.info("loading shapefile: %s", shp_path)
    gdf = gpd.read_file(shp_path, encoding="cp932").to_crs(4326)
    # N03 attributes (canonical):
    #   N03_001 都道府県名, N03_002 支庁名(北海道のみ), N03_003 郡・政令市名,
    #   N03_004 市区町村名, N03_007 行政区域コード (5桁)
    pref_col = "N03_001"
    city_col = "N03_004"
    code_col = "N03_007"

    pref_groups: dict[str, list] = {}
    city_groups: dict[str, dict] = {}

    for _, row in gdf.iterrows():
        prefname = row[pref_col]
        cityname = row.get(city_col) or ""
        citycode = row.get(code_col) or ""
        geom = row.geometry
        if geom is None:
            continue
        pref_groups.setdefault(prefname, []).append(geom)
        if citycode:
            city_groups.setdefault(citycode, {
                "name": cityname,
                "prefname": prefname,
                "geoms": [],
            })["geoms"].append(geom)

    PREF_CODES = _PREF_NAME_TO_CODE
    rows_pref = rows_city = 0

    async with session_scope() as s:
        run_id = await start_run(s, DATASET)
        try:
            # prefectures
            for prefname, geoms in pref_groups.items():
                code = PREF_CODES.get(prefname)
                if not code:
                    logger.warning("unknown prefecture name: %s", prefname)
                    continue
                merged = _multipolygon(geoms)
                await s.execute(
                    text(
                        """
                        INSERT INTO legalshield.prefecture
                          (prefecture_code, name_ja, geom)
                        VALUES (:c, :n, ST_GeogFromText(:wkt))
                        ON CONFLICT (prefecture_code) DO UPDATE
                          SET name_ja = EXCLUDED.name_ja,
                              geom    = EXCLUDED.geom
                        """
                    ),
                    {"c": code, "n": prefname, "wkt": merged.wkt},
                )
                rows_pref += 1

            # cities
            for citycode, info in city_groups.items():
                pcode = PREF_CODES.get(info["prefname"])
                if not pcode:
                    continue
                merged = _multipolygon(info["geoms"])
                await s.execute(
                    text(
                        """
                        INSERT INTO legalshield.city
                          (city_code, prefecture_code, name_ja, geom)
                        VALUES (:cc, :pc, :n, ST_GeogFromText(:wkt))
                        ON CONFLICT (city_code) DO UPDATE
                          SET name_ja = EXCLUDED.name_ja,
                              geom    = EXCLUDED.geom
                        """
                    ),
                    {"cc": citycode, "pc": pcode, "n": info["name"], "wkt": merged.wkt},
                )
                rows_city += 1

            await finish_run(s, run_id, "success",
                             rows_in=len(gdf),
                             rows_out=rows_pref + rows_city,
                             notes=f"prefectures={rows_pref}, cities={rows_city}")
            logger.info("n03 ingest done: pref=%d city=%d", rows_pref, rows_city)
        except Exception as exc:
            await finish_run(s, run_id, "failed", notes=repr(exc))
            raise


def _multipolygon(geoms):
    from shapely.geometry import MultiPolygon, Polygon
    polys = []
    for g in geoms:
        if isinstance(g, Polygon):
            polys.append(g)
        elif isinstance(g, MultiPolygon):
            polys.extend(list(g.geoms))
    return MultiPolygon(polys)


_PREF_NAME_TO_CODE = {
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shp", type=Path, required=True, help="Path to N03 shapefile")
    args = ap.parse_args()
    if not args.shp.exists():
        print(f"Shapefile not found: {args.shp}", file=sys.stderr)
        return 2
    asyncio.run(run(args.shp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
