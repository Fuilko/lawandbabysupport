"""Socio-economic + family + locations data batch (e-Stat).

Covers: income, poverty, household, elderly, single-parent, foreigner,
welfare recipients, unemployment, education, divorce, marriage, birth/death.
"""
from __future__ import annotations

from .batch_fetch import fetch_dataset

PLAN: list[tuple[str, str, int, str | None]] = [
    # 所得・貧困
    ("income_municipal",   "課税対象所得",        15, None),
    ("income_household",   "世帯所得",            15, None),
    ("welfare_recipients", "生活保護",            20, None),
    ("child_poverty",      "子ども 貧困",         10, None),
    ("low_income",         "低所得",              10, None),
    # 世帯・家族
    ("household_compose",  "世帯",                30, None),
    ("single_parent",      "ひとり親",            15, None),
    ("single_mother",      "母子家庭",            10, None),
    ("single_father",      "父子家庭",            5, None),
    ("divorce",            "離婚",                15, None),
    ("marriage",           "婚姻",                10, None),
    ("birth_rate",         "出生",                15, None),
    ("death_rate",         "死亡",                10, None),
    # 人口構造
    ("elderly_ratio",      "高齢化",              15, None),
    ("aging_society",      "老年人口",            10, None),
    ("youth_pop",          "年少人口",            5, None),
    ("foreign_pop",        "外国人住民",          10, None),
    ("depop_rural",        "過疎",                10, None),
    # 雇用・教育
    ("unemployment",       "完全失業",            15, None),
    ("non_regular",        "非正規",              10, None),
    ("wage_gap",           "賃金",                15, None),
    ("women_emp",          "女性 雇用",           10, None),
    ("youth_emp",          "若年者雇用",          5, None),
    ("highschool_dropout", "高校 中退",           5, None),
    # 健康・福祉
    ("mental_health",      "精神保健",            10, None),
    ("disabled_persons",   "障害者数",            10, None),
    ("medical_access",     "医療施設",            10, None),
    # 行政・公共
    ("local_finance",      "地方財政",            15, None),
    ("public_safety",      "防犯",                10, None),
    # 住宅・居住
    ("housing",            "住宅",                15, None),
    ("homeless_count",     "ホームレス 実態",     5, None),
    # 移動
    ("migration",          "人口移動",            10, None),
    # 教育・学校
    ("school_count",       "学校数",              10, None),
    ("library_count",      "図書館",              5, None),
    # 犯罪詳細（追加）
    ("juvenile_offender",  "少年犯罪",            10, None),
    ("stalking",           "ストーカー",          5, None),
    ("cybercrime",         "サイバー犯罪",        5, None),
    ("traffic_fatality",   "交通死亡",            10, None),
]


def main() -> None:
    summary = []
    for d, kw, n, ag in PLAN:
        try:
            summary.append(fetch_dataset(d, kw, n, ag))
        except Exception as e:  # noqa: BLE001
            summary.append({"dataset": d, "ok": 0, "fail": -1, "planned": 0, "err": str(e)})
    print("\n=== SOCIO BATCH SUMMARY ===")
    total_ok = 0
    for s in summary:
        total_ok += max(s.get("ok", 0), 0)
        print(f"  {s['dataset']:24s}  ok={s['ok']:3d}  planned={s['planned']}")
    print(f"\nTOTAL OK tables: {total_ok}")


if __name__ == "__main__":
    main()
