"""Generate 'Law-and-Admin ACCESS FAILURE' heat-map of Japan.

NOTE: We do NOT plot raw crime counts (= a population map).
The Access Failure Score is defined as:

    crime_density   = recognized_total / population        (high = many victims)
    clearance_rate  = cleared / recognized                 (low  = police fails)
    lawyer_density  = lawyers / 100k population            (low  = no legal help)
    ngo_density     = ngo_count_seed / 100k                (low  = no NPO)

    failure = (crime_density * (1 - clearance_rate))
              / (lawyer_density * (1 + ngo_density))

Higher value = harder for a victim to obtain justice in that prefecture.
Expected ranking: rural prefectures (高知, 島根, 鳥取, 秋田...) high;
Tokyo / Osaka low because they have many lawyers / NPOs.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import folium
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
DUCKDB_PATH = KNOWLEDGE / "unified.duckdb"
PARSED = KNOWLEDGE / "parsed"
GEOJSON_URL = "https://raw.githubusercontent.com/dataofjapan/land/master/japan.geojson"
GEOJSON_LOCAL = KNOWLEDGE / "japan.geojson"

PREF47 = [
    "北海道","青森県","岩手県","宮城県","秋田県","山形県","福島県",
    "茨城県","栃木県","群馬県","埼玉県","千葉県","東京都","神奈川県",
    "新潟県","富山県","石川県","福井県","山梨県","長野県",
    "岐阜県","静岡県","愛知県","三重県",
    "滋賀県","京都府","大阪府","兵庫県","奈良県","和歌山県",
    "鳥取県","島根県","岡山県","広島県","山口県",
    "徳島県","香川県","愛媛県","高知県",
    "福岡県","佐賀県","長崎県","熊本県","大分県","宮崎県","鹿児島県","沖縄県",
]


def _download_geojson() -> Path:
    if GEOJSON_LOCAL.exists() and GEOJSON_LOCAL.stat().st_size > 1000:
        return GEOJSON_LOCAL
    import urllib.request
    print(f"downloading {GEOJSON_URL}")
    urllib.request.urlretrieve(GEOJSON_URL, GEOJSON_LOCAL)
    return GEOJSON_LOCAL


def _attach_views(con):
    for d in sorted(PARSED.iterdir()):
        if not d.is_dir():
            continue
        files = [f for f in d.glob("*.parquet") if f.stat().st_size > 200]
        if not files:
            continue
        pattern = str(d / "*.parquet").replace("\\", "/")
        try:
            con.execute(
                f'CREATE OR REPLACE VIEW "{d.name}" AS SELECT * FROM read_parquet(\'{pattern}\', union_by_name=true)'
            )
        except Exception:
            pass


RES_CSV = ROOT / "knowledge" / "seeds" / "pref_resources.csv"


def _aggregate_by_pref(con) -> pd.DataFrame:
    """Aggregate per-prefecture crime totals, separating 認知 / 検挙 if possible."""
    # Try to use tab_name to split 認知 vs 検挙
    sql = """
    WITH src AS (
        SELECT area_name AS pref,
               COALESCE(tab_name, '') AS tab,
               TRY_CAST(value AS DOUBLE) AS v
        FROM crime_npa
        WHERE area_name IS NOT NULL
          AND value IS NOT NULL AND value != ''
    )
    SELECT pref,
           SUM(CASE WHEN tab LIKE '%認知%' THEN v ELSE 0 END) AS recognized,
           SUM(CASE WHEN tab LIKE '%検挙件数%' OR tab LIKE '%検挙数%' THEN v ELSE 0 END) AS cleared,
           SUM(v) AS total_value,
           COUNT(*) AS n_rows
    FROM src
    WHERE pref IN (SELECT UNNEST(?))
    GROUP BY pref
    """
    df = con.execute(sql, [PREF47]).fetchdf()
    return df


def _compute_failure_score(df_crime: pd.DataFrame) -> pd.DataFrame:
    """Composite "access failure" score.

    Two evidence-based, easy-to-defend metrics combined:

      A. citizens_per_lawyer = population / lawyers
         (high = scarce legal help; Japan avg ~3,000; 高知 ~7,700, 東京 ~650)

      B. ngo_density_inverse = 1 / (1 + ngo_count_seed)
         (low ngo seed => closer to 1.0; high ngo => smaller multiplier)

      score_raw = citizens_per_lawyer * ngo_density_inverse
      score     = (score_raw - min) / (max - min) * 100   (0..100)

    This is a *legal-resource access* heat-map, not a crime map.
    Absolute crime counts in the e-Stat tables we fetched are YoY-change
    tables, so we don't use them here.
    """
    res = pd.read_csv(RES_CSV)
    df = res.copy()
    df["citizens_per_lawyer"] = df["population_2020"] / df["lawyers_2023"]
    df["lawyers_per_100k"]    = df["lawyers_2023"] / df["population_2020"] * 100_000.0
    df["ngo_per_100k"]        = df["ngo_count_seed"] / df["population_2020"] * 100_000.0
    df["ngo_inverse"]         = 1.0 / (1.0 + df["ngo_count_seed"])
    df["failure_raw"]         = df["citizens_per_lawyer"] * df["ngo_inverse"]
    lo, hi = df["failure_raw"].min(), df["failure_raw"].max()
    df["score"] = (df["failure_raw"] - lo) / (hi - lo + 1e-9) * 100.0
    # Stub kept for tooltip compatibility
    df["crime_per_100k"]  = 0.0
    df["clearance_rate"]  = 0.40
    df = df.rename(columns={"prefecture": "pref"})
    return df


def build() -> Path:
    geo = _download_geojson()
    con = duckdb.connect(str(DUCKDB_PATH))
    _attach_views(con)
    df_crime = _aggregate_by_pref(con)
    if df_crime.empty:
        raise SystemExit("no prefecture-level data found; run crawlers first")

    df = _compute_failure_score(df_crime)
    print("\n=== ACCESS FAILURE RANKING (top 15 = worst) ===")
    cols = ["pref", "score", "citizens_per_lawyer", "lawyers_2023",
            "ngo_count_seed", "population_2020"]
    print(df.sort_values("score", ascending=False).head(15)[cols].to_string(index=False))
    print("\n=== BEST (bottom 5 = easiest) ===")
    print(df.sort_values("score").head(5)[cols].to_string(index=False))

    # Merge score back into GeoJSON for rich tooltips
    gj = json.loads(geo.read_text(encoding="utf-8"))
    sample = gj["features"][0]["properties"]
    key = "nam_ja" if "nam_ja" in sample else ("name_ja" if "name_ja" in sample else list(sample)[0])

    score_map = df.set_index("pref").to_dict("index")
    for feat in gj["features"]:
        name = feat["properties"].get(key)
        rec = score_map.get(name) or {}
        feat["properties"]["score"] = round(rec.get("score", 0), 1)
        feat["properties"]["citizens_per_lawyer"] = int(rec.get("citizens_per_lawyer", 0) or 0)
        feat["properties"]["lawyers"] = int(rec.get("lawyers_2023", 0) or 0)
        feat["properties"]["lawyers_per_100k"] = round(rec.get("lawyers_per_100k", 0), 2)
        feat["properties"]["ngo_seed"] = int(rec.get("ngo_count_seed", 0) or 0)
        feat["properties"]["population"] = int(rec.get("population_2020", 0) or 0)

    m = folium.Map(location=[37.5, 137.0], zoom_start=5, tiles="cartodbpositron")

    folium.Choropleth(
        geo_data=gj,
        data=df,
        columns=["pref", "score"],
        key_on=f"feature.properties.{key}",
        fill_color="YlOrRd",
        fill_opacity=0.8,
        line_opacity=0.3,
        legend_name="法律・行政アクセス困難スコア (0=容易 / 100=困難)",
        nan_fill_color="#cccccc",
        bins=[0, 10, 20, 30, 45, 60, 80, 100],
    ).add_to(m)

    folium.GeoJson(
        gj,
        name="prefectures",
        style_function=lambda f: {"fillOpacity": 0, "color": "#333", "weight": 0.6},
        tooltip=folium.features.GeoJsonTooltip(
            fields=[key, "score", "citizens_per_lawyer",
                    "lawyers", "lawyers_per_100k", "ngo_seed", "population"],
            aliases=["都道府県", "困難スコア (0-100)", "弁護士1人あたり住民数",
                     "弁護士数 (2023)", "弁護士/10万人",
                     "NPO seed", "人口 (2020)"],
            localize=True,
            sticky=True,
        ),
    ).add_to(m)

    # Description card
    title_html = """
    <div style="position: fixed; top: 12px; left: 60px; z-index:9999;
                background: rgba(11,16,32,0.92); color:#e6ecff; padding:14px 18px;
                border:1px solid #243260; border-radius:10px; max-width:520px;
                font-family:'Hiragino Sans','Yu Gothic UI','Noto Sans JP',sans-serif;
                font-size:13px; line-height:1.5;">
      <div style="font-size:16px; color:#7cf0c2; font-weight:700; margin-bottom:6px">
        法律・行政が伸張しない日本マップ
      </div>
      <div>
        スコア = (住民数 ÷ 弁護士数) × (1 ÷ (1 + NPO seed数))<br>
        <b>赤 = 弁護士1人で何千人を担当する地域</b>　青 = 法律・NPO 資源が充実<br>
        例: 高知 7,684 人/弁護士 ↔ 東京 653 人/弁護士（約 12 倍格差）
      </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    out = ROOT / "JAPAN_HEATMAP.html"
    m.save(str(out))
    df.sort_values("score", ascending=False).to_csv(
        ROOT / "knowledge" / "access_failure_ranking.csv", index=False, encoding="utf-8-sig"
    )
    print(f"[ok] wrote {out}")
    return out


if __name__ == "__main__":
    build()
