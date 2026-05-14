"""Aggregate municipal-level e-Stat data up to prefecture level.

Reads all parsed municipal tables, extracts area_code/area_name,
groups by prefecture, and writes unified prefecture-level Parquet files.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
PARSED = KNOWLEDGE / "parsed"
OUT = KNOWLEDGE / "muni_aggregated"
OUT.mkdir(exist_ok=True)

# 47 prefecture name → canonical prefix for matching
PREF_PREFIXES = [
    "北海道","青森","岩手","宮城","秋田","山形","福島",
    "茨城","栃木","群馬","埼玉","千葉","東京","神奈川",
    "新潟","富山","石川","福井","山梨","長野",
    "岐阜","静岡","愛知","三重",
    "滋賀","京都","大阪","兵庫","奈良","和歌山",
    "鳥取","島根","岡山","広島","山口",
    "徳島","香川","愛媛","高知",
    "福岡","佐賀","長崎","熊本","大分","宮崎","鹿児島","沖縄",
]


def _match_pref(area_name: str | None) -> str | None:
    if not area_name:
        return None
    s = str(area_name)
    for p in PREF_PREFIXES:
        if s.startswith(p):
            return p + ("県" if p not in ("東京都","京都府","大阪府","北海道") else ("都" if p=="東京" else "府" if p in ("京都","大阪") else "道"))
    return None


def aggregate_dataset(dataset_dir: Path) -> pd.DataFrame | None:
    files = [f for f in dataset_dir.glob("*.parquet") if f.stat().st_size > 200 and "catalog" not in f.name]
    if not files:
        return None
    con = duckdb.connect()
    pattern = str(dataset_dir / "*.parquet").replace("\\", "/")
    # exclude catalog files
    sql = f"""
    SELECT * FROM read_parquet('{pattern}', union_by_name=true)
    WHERE area_name IS NOT NULL AND area_name != ''
      AND value IS NOT NULL AND value != ''
    """
    try:
        df = con.execute(sql).fetchdf()
    except Exception:
        return None
    if df.empty or "area_name" not in df.columns:
        return None
    df["pref"] = df["area_name"].apply(_match_pref)
    df = df[df["pref"].notna()]
    if df.empty:
        return None
    # sum numeric values per pref
    df["v"] = pd.to_numeric(df["value"], errors="coerce")
    agg = df.groupby("pref")["v"].sum().reset_index()
    agg.columns = ["pref", dataset_dir.name]
    return agg


def main() -> None:
    datasets = [d for d in sorted(PARSED.iterdir()) if d.is_dir() and d.name.startswith(("muni_", "census", "juki_", "eco_", "school_", "housing_", "national_", "nursing_", "pension_", "welfare_detail", "child_welfare", "elderly_welfare", "care_facility", "hospital_", "land_use", "vacant_house", "public_safety", "disaster", "agriculture", "forestry", "migration_in"))]
    print(f"found {len(datasets)} municipal datasets")
    merged: pd.DataFrame | None = None
    for d in datasets:
        agg = aggregate_dataset(d)
        if agg is None:
            continue
        print(f"  {d.name:32s}  rows={len(agg)}")
        if merged is None:
            merged = agg
        else:
            merged = merged.merge(agg, on="pref", how="outer")
    if merged is not None:
        out = OUT / "prefecture_aggregated.parquet"
        merged.to_parquet(out)
        csv_out = OUT / "prefecture_aggregated.csv"
        merged.to_csv(csv_out, index=False, encoding="utf-8-sig")
        print(f"[ok] wrote {out}  rows={len(merged)}  cols={list(merged.columns)}")
    else:
        print("[warn] no aggregable municipal data found")


if __name__ == "__main__":
    main()
