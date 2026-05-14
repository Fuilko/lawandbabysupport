"""Multi-axis trend & correlation analysis.

Combines per-prefecture metrics across:
  - 法律資源    : 弁護士数, NPO seed
  - 犯罪      : 認知件数, 検挙率 (when available)
  - 社経      : 課税対象所得, 生活保護率, 完全失業率
  - 家族      : 離婚, ひとり親, 高齢化, 出生
  - インフラ   : 裁判所・検察庁・法テラス位置数

Outputs:
  - TRENDS_REPORT.html (heatmap + correlation matrix + ranked tables)
  - knowledge/composite_index.csv
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
PARSED = KNOWLEDGE / "parsed"
DUCKDB_PATH = KNOWLEDGE / "unified.duckdb"

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
                f'CREATE OR REPLACE VIEW "{d.name}" AS '
                f"SELECT * FROM read_parquet('{pattern}', union_by_name=true)"
            )
        except Exception:
            pass


def _safe_pref_agg(con, view: str, agg: str = "SUM") -> pd.DataFrame:
    """Aggregate `value` per area_name (if view has it) restricted to 47 prefs.

    Returns DataFrame[pref, value].
    """
    try:
        cols = [c[0] for c in con.execute(f'DESCRIBE "{view}"').fetchall()]
    except Exception:
        return pd.DataFrame(columns=["pref", "value"])
    if "area_name" not in cols or "value" not in cols:
        return pd.DataFrame(columns=["pref", "value"])
    sql = f"""
    SELECT area_name AS pref,
           {agg}(TRY_CAST(value AS DOUBLE)) AS value
    FROM "{view}"
    WHERE area_name IN (SELECT UNNEST(?))
      AND value IS NOT NULL AND value != ''
    GROUP BY area_name
    """
    try:
        return con.execute(sql, [PREF47]).fetchdf()
    except Exception:
        return pd.DataFrame(columns=["pref", "value"])


# Map metric -> (view name, aggregator)
METRICS = {
    "income_total":        ("income_municipal",   "SUM"),
    "welfare":             ("welfare_recipients", "SUM"),
    "child_poverty":       ("child_poverty",      "SUM"),
    "single_parent":       ("single_parent",      "SUM"),
    "divorce":             ("divorce",            "SUM"),
    "elderly":             ("elderly_ratio",      "SUM"),
    "unemployment":        ("unemployment",       "SUM"),
    "non_regular":         ("non_regular",        "SUM"),
    "homeless":            ("homeless_count",     "SUM"),
    "youth_offender":      ("juvenile_offender",  "SUM"),
    "suicide":             ("suicide_stats",      "SUM"),
    "dv_consultation":     ("dv_consultation",    "SUM"),
    "child_abuse":         ("child_abuse",        "SUM"),
    "foreign_pop":         ("foreign_pop",        "SUM"),
    "household":           ("household_compose",  "SUM"),
}


def build_composite() -> pd.DataFrame:
    con = duckdb.connect(str(DUCKDB_PATH))
    _attach_views(con)
    res = pd.read_csv(KNOWLEDGE / "seeds" / "pref_resources.csv")
    df = res.copy().rename(columns={"prefecture": "pref"})

    available = []
    for key, (view, agg) in METRICS.items():
        sub = _safe_pref_agg(con, view, agg)
        if sub.empty:
            continue
        sub = sub.rename(columns={"value": key})
        df = df.merge(sub, on="pref", how="left")
        available.append(key)

    df.to_csv(KNOWLEDGE / "composite_metrics.csv", index=False, encoding="utf-8-sig")

    # Normalize each available metric per-capita (when meaningful)
    pop = df["population_2020"]
    for k in available:
        df[f"{k}_per_100k"] = df[k] / pop * 100_000.0

    # Composite hardship: sum of normalized adversity metrics minus normalized resources
    adversity = [c for c in df.columns if c.endswith("_per_100k") and c not in (
        "income_total_per_100k",  # income is RESOURCE not adversity
    )]

    norm = df[adversity].apply(lambda s: (s - s.min()) / (s.max() - s.min() + 1e-9))
    df["adversity_score"] = norm.sum(axis=1) / max(len(adversity), 1) * 100.0

    df["lawyers_per_100k"] = df["lawyers_2023"] / pop * 100_000.0
    lawyers_norm = df["lawyers_per_100k"]
    lawyers_n = (lawyers_norm - lawyers_norm.min()) / (lawyers_norm.max() - lawyers_norm.min() + 1e-9)
    ngo_norm = df["ngo_count_seed"] / (pop / 100_000.0)
    ngo_n = (ngo_norm - ngo_norm.min()) / (ngo_norm.max() - ngo_norm.min() + 1e-9)
    df["resource_score"] = (lawyers_n * 0.7 + ngo_n * 0.3) * 100.0

    df["legal_failure_score"] = (df["adversity_score"] - df["resource_score"] * 0.5).clip(lower=0)
    df.to_csv(KNOWLEDGE / "composite_index.csv", index=False, encoding="utf-8-sig")

    return df.sort_values("legal_failure_score", ascending=False)


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in df.columns if c.endswith("_per_100k") or c in (
        "lawyers_per_100k", "score", "adversity_score", "resource_score",
        "legal_failure_score", "citizens_per_lawyer"
    )]
    cols = [c for c in cols if c in df.columns and df[c].notna().sum() > 5]
    return df[cols].corr().round(2)


def build_report() -> Path:
    df = build_composite()
    corr = correlation_matrix(df)

    top = df.head(15)[["pref", "legal_failure_score", "adversity_score",
                       "resource_score", "lawyers_per_100k"]].round(1)
    bot = df.tail(5)[["pref", "legal_failure_score", "adversity_score",
                      "resource_score", "lawyers_per_100k"]].round(1)

    def tbl(d):
        return d.to_html(index=False, classes="t", border=0)

    css = """
    body{margin:0;background:#0b1020;color:#e6ecff;font-family:-apple-system,'Hiragino Sans','Noto Sans JP',sans-serif;line-height:1.55}
    main{max-width:1200px;margin:0 auto;padding:24px}
    header{padding:24px;background:linear-gradient(135deg,#1a2a6c,#0b1020);border-bottom:1px solid #243260}
    h1{margin:0;font-size:22px} h2{color:#7cf0c2;margin-top:32px}
    section{background:#121a33;border:1px solid #243260;border-radius:12px;padding:18px;margin:18px 0}
    table.t{width:100%;border-collapse:collapse;font-size:12px}
    table.t th,table.t td{border-bottom:1px solid #243260;padding:6px 8px;text-align:left}
    table.t th{background:#172246;color:#ffd166}
    .callout{background:#0f1a36;border-left:4px solid #7cf0c2;padding:10px 14px;border-radius:8px}
    """

    cm_html = corr.to_html(classes="t", border=0)

    html = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
    <title>LegalShield 複合指標トレンド</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>{css}</style></head><body>
    <header><h1>LegalShield 複合指標 & トレンド分析</h1>
    <div style="color:#9aa7d0;font-size:12px">利用可能なすべての軸 (犯罪・貧困・家族・雇用・福祉・士業資源) を統合</div>
    </header>
    <main>
      <section>
        <h2>方法論</h2>
        <div class="callout">
        <b>adversity_score</b> = 困窮系メトリクス（生活保護・自殺・離婚・DV・児童虐待・失業・ひとり親 等）を都道府県人口あたりに正規化し平均<br>
        <b>resource_score</b> = (弁護士密度 × 0.7 + NPO密度 × 0.3)<br>
        <b>legal_failure_score</b> = adversity - 0.5 × resource (clip ≥ 0)<br>
        高 = 困窮が多く救済資源が乏しい
        </div>
      </section>
      <section><h2>困難度ランキング (Top 15)</h2>{tbl(top)}</section>
      <section><h2>最も恵まれた地域 (Bottom 5)</h2>{tbl(bot)}</section>
      <section><h2>相関行列 (Pearson)</h2>
        <div style="overflow-x:auto;font-size:11px">{cm_html}</div>
      </section>
      <section><h2>解釈ヒント</h2>
        <ul>
          <li>弁護士密度と所得は強い正相関（東京・大阪に集中）</li>
          <li>生活保護率と離婚率は中相関と予測（家族解体）</li>
          <li>高齢化と過疎は司法アクセスを物理的に阻む</li>
          <li>外国人住民比率と多言語対応の不足はギャップ指標</li>
        </ul>
      </section>
    </main></body></html>"""
    out = ROOT / "TRENDS_REPORT.html"
    out.write_text(html, encoding="utf-8")
    print(f"[ok] wrote {out}")
    print(f"[ok] CSV: {KNOWLEDGE / 'composite_index.csv'}")
    return out


if __name__ == "__main__":
    build_report()
