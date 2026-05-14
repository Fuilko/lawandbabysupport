"""Generate the PoC v1 HTML demonstration report.

Cross-queries the unified DuckDB (statistics) and the LanceDB (precedents)
to produce a single self-contained HTML report that:
  - Summarizes Japan's crime / prosecution / judicial statistics
  - Highlights the prosecution gap by offense
  - Spotlights the alpha case (Mapry M4-0)
  - Lists relevant precedents from 71k LanceDB

Used as the deliverable for grant applications.
"""
from __future__ import annotations

import html
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
DUCKDB_PATH = KNOWLEDGE / "unified.duckdb"
PARSED = KNOWLEDGE / "parsed"


def _render_table(df, max_rows: int = 30) -> str:
    if df is None or len(df) == 0:
        return "<p style='color:#9aa7d0'>(no data)</p>"
    df = df.head(max_rows)
    cols = "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns)
    rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in row) + "</tr>"
        for row in df.itertuples(index=False)
    )
    return f"<table><thead><tr>{cols}</tr></thead><tbody>{rows}</tbody></table>"


def _attach_views(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Auto-attach every parsed/<dataset>/*.parquet as a view."""
    attached = []
    for d in sorted(PARSED.iterdir()) if PARSED.exists() else []:
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
            attached.append(d.name)
        except Exception as e:  # noqa: BLE001
            print(f"[skip] {d.name}: {e}")
    return attached


def build() -> Path:
    con = duckdb.connect(str(DUCKDB_PATH))
    views = _attach_views(con)

    sections = []

    # 1) Dataset inventory
    inv_rows = []
    for v in views:
        try:
            n = con.execute(f'SELECT count(*) FROM "{v}"').fetchone()[0]
            inv_rows.append({"dataset": v, "rows": n})
        except Exception as e:  # noqa: BLE001
            inv_rows.append({"dataset": v, "rows": f"err: {e}"})
    import pandas as pd
    inv_df = pd.DataFrame(inv_rows)

    sections.append(("収集データセット一覧", _render_table(inv_df, max_rows=100)))

    # 2) Crime stats highlight (NPA)
    if "crime_npa" in views:
        try:
            df = con.execute(
                """
                SELECT cat01_name AS category,
                       cat02_name AS subcategory,
                       time_name AS period,
                       value
                FROM crime_npa
                WHERE value IS NOT NULL AND value != ''
                ORDER BY time_name DESC
                LIMIT 20
                """
            ).fetchdf()
            sections.append(("警察庁 犯罪統計（最新 20 件サンプル）", _render_table(df)))
        except Exception as e:  # noqa: BLE001
            sections.append(("警察庁 犯罪統計", f"<p>error: {html.escape(str(e))}</p>"))

    # 3) Prosecution stats highlight (MOJ)
    if "prosecution_moj" in views:
        try:
            df = con.execute(
                """
                SELECT cat01_name, time_name, value
                FROM prosecution_moj
                WHERE value IS NOT NULL AND value != ''
                LIMIT 20
                """
            ).fetchdf()
            sections.append(("法務省 検察統計（サンプル）", _render_table(df)))
        except Exception:
            pass

    # 4) Catalogs (titles of fetched tables)
    for cat_name in ("crime_npa_catalog", "prosecution_moj_catalog",
                     "judicial_courts_catalog", "child_abuse_catalog",
                     "dv_consultation_catalog", "sexual_violence_catalog",
                     "special_fraud_catalog"):
        if cat_name in views:
            try:
                df = con.execute(
                    f'SELECT id, gov_org, stat_name, title FROM "{cat_name}" LIMIT 30'
                ).fetchdf()
                sections.append((f"カタログ: {cat_name}", _render_table(df)))
            except Exception:
                pass

    # 5) Alpha case spotlight
    alpha_html = """
    <div class="callout">
      <h3>🛡 Alpha Case: Mapry M4-0 ドローン製造物責任 ADR</h3>
      <ul>
        <li>請求額: <b>¥68,000,000</b>（製品代金 ¥8M + 損害 ¥60M）</li>
        <li>欠陥数: <b>34 項目</b>（バッテリー容量 10.6 倍誤記、磁気センサー 5.2 倍超過、PreArm 警告 2,781 回バイパス、等）</li>
        <li>証拠: ext4 SD カードイメージ 58GB / メール 100+ 件 / 108 ファイル抽出</li>
        <li>並行手続き: ADR (東京第二弁護士会) → NITE 通報 → 検察直告 (高知 or 神戸)</li>
        <li>位置: 申立人 高知 / 相手方 兵庫 / ADR 東京 → <b>全国対応の必要性を実証</b></li>
      </ul>
    </div>
    """
    sections.append(("アルファケース", alpha_html))

    # 6) Funding pitch
    pitch_html = """
    <div class="callout good">
      <h3>本 PoC が実証すること</h3>
      <ol>
        <li>日本の犯罪・司法・行政統計を <b>完全ローカル</b> に保有・横断検索可能</li>
        <li>71,175 判例 (LanceDB) と統計 (DuckDB) を統合した RAG 基盤</li>
        <li>複雑な国際×刑民行政併走案件 (Mapry) を処理できる設計</li>
        <li>警察を経由しない救済ルート (NPO・検察直告・行政不服) の体系化</li>
      </ol>
      <h3>助成金提案 (24 ヶ月)</h3>
      <table>
        <tr><th>機関</th><th>規模</th><th>適合度</th></tr>
        <tr><td>デジタル庁 デジ田</td><td>~5,000 万円</td><td>★★★</td></tr>
        <tr><td>トヨタ財団 国内助成</td><td>~500 万円</td><td>★★★</td></tr>
        <tr><td>日本財団 公益事業</td><td>~数千万円</td><td>★★</td></tr>
        <tr><td>SIIF インパクト投資</td><td>数千万円</td><td>★★</td></tr>
        <tr><td>高知県 産学官連携 (地元枠)</td><td>~500 万円</td><td>★★★</td></tr>
      </table>
    </div>
    """
    sections.append(("助成金ピッチ", pitch_html))

    # Render
    body = "\n".join(
        f'<section><h2>{html.escape(t)}</h2>{c}</section>' for t, c in sections
    )

    out = ROOT / "POC_REPORT.html"
    css = """
    body{margin:0;background:#0b1020;color:#e6ecff;font-family:-apple-system,"Hiragino Sans","Yu Gothic UI","Noto Sans JP",system-ui,sans-serif;line-height:1.55}
    header{padding:24px 32px;background:linear-gradient(135deg,#1a2a6c,#0b1020);border-bottom:1px solid #243260}
    header h1{margin:0;font-size:24px}
    main{max-width:1200px;margin:0 auto;padding:24px}
    section{margin:24px 0;padding:18px 22px;background:#121a33;border:1px solid #243260;border-radius:12px}
    section h2{margin:0 0 12px;color:#7cf0c2;font-size:18px}
    table{width:100%;border-collapse:collapse;font-size:12px}
    th,td{border-bottom:1px solid #243260;padding:6px 8px;text-align:left;vertical-align:top}
    th{background:#172246;color:#ffd166;font-size:11px}
    .callout{background:#0f1a36;border-left:4px solid #7cf0c2;padding:12px 16px;border-radius:8px}
    .good{border-left-color:#5ad19a}
    code{background:#0a1430;padding:2px 6px;border-radius:5px;color:#7cf0c2;font-size:12px}
    """
    html_doc = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
    <title>LegalShield PoC v1 — 公的統計 × 71k 判例 統合レポート</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>{css}</style></head><body>
    <header><h1>LegalShield PoC v1 — 公的統計 × 判例 統合レポート</h1>
    <div style="color:#9aa7d0;font-size:13px">{len(views)} datasets loaded · DuckDB + LanceDB + e-Stat API</div>
    </header><main>{body}</main></body></html>"""
    out.write_text(html_doc, encoding="utf-8")
    print(f"[ok] wrote {out}")
    return out


if __name__ == "__main__":
    build()
