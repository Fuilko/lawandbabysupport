"""市区町村レベルのデータバッチ。

e-Stat には 1,741 市区町村別の所得・人口・福祉統計が大量にある。
ここでは「自治体ベンチマーク」相当の基幹統計を一気に取得する。
"""
from __future__ import annotations

from .batch_fetch import fetch_dataset

PLAN: list[tuple[str, str, int, str | None]] = [
    # 統計でみる都道府県・市区町村のすがた (社会・人口統計体系)
    ("muni_overview",       "市区町村のすがた",  30, None),
    ("muni_society",        "社会人口統計体系",  30, None),
    # 国勢調査 (最も網羅的)
    ("census",              "国勢調査",          50, None),
    ("census_household",    "国勢調査 世帯",     30, None),
    ("census_age",          "国勢調査 年齢",     20, None),
    ("census_foreign",      "国勢調査 外国人",   10, None),
    # 経済センサス
    ("eco_census",          "経済センサス",      20, None),
    # 住民基本台帳
    ("juki_pop",            "住民基本台帳 人口", 30, None),
    ("juki_movement",       "住民基本台帳 移動", 15, None),
    # 市町村税
    ("muni_tax",            "市町村税",          15, None),
    ("muni_finance",        "市町村財政",        15, None),
    # 国保・介護・年金
    ("national_insurance",  "国民健康保険",      15, None),
    ("nursing_care",        "介護保険",          20, None),
    ("pension_local",       "国民年金",          10, None),
    # 福祉 細目
    ("welfare_detail",      "福祉行政",          15, None),
    ("child_welfare",       "児童福祉",          15, None),
    ("elderly_welfare",     "老人福祉",          10, None),
    # 教育 細目
    ("school_basic",        "学校基本調査",      30, None),
    ("school_lunch",        "学校給食",          5, None),
    # 警察署・交番統計
    ("police_station",      "警察署",            5, None),
    # 都市計画・住宅
    ("housing_survey",      "住宅 土地",         20, None),
    ("vacant_house",        "空き家",            10, None),
    # 防災・災害
    ("disaster",            "災害",              10, None),
    # 産業・農林
    ("agriculture",         "農林業センサス",    15, None),
    ("forestry",            "林業 統計",         10, None),
    # 観光・移住
    ("migration_in",        "移住",              5, None),
    # 介護施設
    ("care_facility",       "介護施設",          10, None),
    # 医療
    ("hospital_survey",     "医療施設調査",      15, None),
    # 国土
    ("land_use",            "土地利用",          5, None),
]


def main() -> None:
    summary = []
    for d, kw, n, ag in PLAN:
        try:
            summary.append(fetch_dataset(d, kw, n, ag))
        except Exception as e:  # noqa: BLE001
            summary.append({"dataset": d, "ok": 0, "fail": -1, "planned": 0, "err": str(e)})
    total_ok = sum(max(s.get("ok", 0), 0) for s in summary)
    print("\n=== MUNICIPAL BATCH SUMMARY ===")
    for s in summary:
        print(f"  {s['dataset']:24s}  ok={s['ok']:3d}  planned={s['planned']}")
    print(f"\nTOTAL OK tables: {total_ok}")


if __name__ == "__main__":
    main()
