"""
JUDB (Japan Underreporting Database) helper.

DuckDB ベースの単一ファイル DB。
- スキーマ初期化
- npa_stalking JSONL → observations への ETL
- 3 キラー指標の取得

使い方:
    from legalshield.db.judb import JUDB
    j = JUDB(); j.init_schema()
    j.ingest_npa_stalking_jsonl(Path("...stats_xxx.jsonl"))
    print(j.gap_coefficient(crime_category="stalking"))
"""
from __future__ import annotations

import hashlib
import json
import logging
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path
from typing import Iterable, Iterator, Optional

import duckdb

logger = logging.getLogger("judb")

DEFAULT_DB = Path(__file__).resolve().parents[1] / "lancedb" / "judb.duckdb"
SCHEMA_SQL = Path(__file__).with_name("judb_schema.sql")

# npa_stalking JSONL の stats フィールド → metric_name / crime_category
_NPA_METRIC_MAP = {
    "stalker_soudan":         ("stalking", "soudan_kensu"),
    "stalker_kenkyo":         ("stalking", "kenkyo_kensu"),
    "stalker_keikoku":        ("stalking", "keikoku_kensu"),
    "stalker_kinshi_meirei":  ("stalking", "kinshi_meirei"),
    "dv_soudan":              ("dv", "soudan_kensu"),
    "dv_kenkyo":              ("dv", "kenkyo_kensu"),
}


class JUDB:
    def __init__(self, db_path: Path = DEFAULT_DB):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[duckdb.DuckDBPyConnection]:
        con = duckdb.connect(str(self.db_path))
        try:
            yield con
        finally:
            con.close()

    # ------------------------------------------------------------------ schema
    def init_schema(self) -> None:
        sql = SCHEMA_SQL.read_text(encoding="utf-8")
        with self.connect() as con:
            # DuckDB doesn't support ON CONFLICT DO NOTHING in INSERT directly the same way;
            # but DuckDB >= 0.9 supports it. Try; on failure, fallback to per-statement run.
            try:
                con.execute(sql)
            except duckdb.Error as e:
                logger.warning("bulk execute failed (%s); falling back to statement-by-statement", e)
                for stmt in _split_sql_statements(sql):
                    try:
                        con.execute(stmt)
                    except duckdb.Error as e2:
                        logger.warning("stmt failed: %s\n%s", e2, stmt[:200])
        logger.info("schema initialized at %s", self.db_path)

    # ------------------------------------------------------------------ ETL
    def ingest_npa_stalking_jsonl(self, jsonl_path: Path) -> int:
        """npa_stalking が出力した JSONL を observations に流し込む。"""
        n = 0
        with self.connect() as con, jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                n += self._ingest_npa_row(con, row)
        logger.info("ingested %d observations from %s", n, jsonl_path)
        return n

    def _ingest_npa_row(self, con: duckdb.DuckDBPyConnection, row: dict) -> int:
        fy = row.get("fiscal_year")
        if fy is None:
            return 0
        period_start = date(fy, 1, 1)
        period_end = date(fy, 12, 31)
        stats = row.get("stats") or {}
        inserted = 0
        for stat_key, value in stats.items():
            if value is None:
                continue
            mapping = _NPA_METRIC_MAP.get(stat_key)
            if not mapping:
                continue
            crime_cat, metric = mapping
            obs_id = self._make_obs_id(
                source=row.get("source", "npa"),
                period=str(fy),
                geo="national",
                metric=f"{crime_cat}:{metric}",
                extra=stat_key,
            )
            con.execute(
                """
                INSERT OR REPLACE INTO observations (
                    obs_id, source, source_dataset, source_url, source_doc_sha256,
                    fetched_at, period_type, period_start, period_end,
                    reiwa_year, fiscal_year,
                    geo_level, prefecture_code, prefecture_name,
                    crime_category, victim_attr,
                    metric_name, metric_value, metric_unit,
                    raw_text, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    obs_id,
                    "npa", "npa_stalking_annual",
                    row.get("url"), row.get("sha256"),
                    row.get("fetched_at") or datetime.utcnow().isoformat(),
                    "annual", period_start, period_end,
                    row.get("reiwa_year"), fy,
                    "national", None, None,
                    crime_cat, "all",
                    metric, float(value), "count",
                    f"npa_stalking R{row.get('reiwa_year')} stat={stat_key}",
                    "high",
                ],
            )
            inserted += 1
        return inserted

    @staticmethod
    def _make_obs_id(source: str, period: str, geo: str, metric: str, extra: str = "") -> str:
        h = hashlib.sha256(f"{source}|{period}|{geo}|{metric}|{extra}".encode()).hexdigest()[:6]
        return f"{source}:{period}:{geo}:{metric}:{h}"

    # ------------------------------------------------------------------ killer metrics
    def gap_coefficient(self, crime_category: str = "stalking", fiscal_year: Optional[int] = None):
        """ギャップ係数: 相談 ÷ 検挙。"""
        q = """
        SELECT crime_category, fiscal_year, prefecture_name,
               soudan_kensu, kenkyo_kensu, gap_coefficient
        FROM v_gap_coefficient
        WHERE crime_category = ?
        """
        params: list = [crime_category]
        if fiscal_year is not None:
            q += " AND fiscal_year = ?"
            params.append(fiscal_year)
        q += " ORDER BY fiscal_year DESC, prefecture_name NULLS LAST"
        with self.connect() as con:
            return con.execute(q, params).fetchall()

    def national_trend(self, crime_category: Optional[str] = None):
        q = "SELECT crime_category, metric_name, fiscal_year, total_value FROM v_national_trend"
        params: list = []
        if crime_category:
            q += " WHERE crime_category = ?"
            params.append(crime_category)
        q += " ORDER BY crime_category, metric_name, fiscal_year"
        with self.connect() as con:
            return con.execute(q, params).fetchall()

    def silence_rates(self):
        with self.connect() as con:
            return con.execute("SELECT * FROM v_silence_rate ORDER BY fiscal_year DESC").fetchall()


def _split_sql_statements(sql: str) -> Iterable[str]:
    """雑な ; 区切り (コメント考慮)。"""
    out, buf = [], []
    for line in sql.splitlines():
        if line.strip().startswith("--"):
            continue
        buf.append(line)
        if line.strip().endswith(";"):
            stmt = "\n".join(buf).strip()
            if stmt:
                out.append(stmt)
            buf = []
    if buf:
        last = "\n".join(buf).strip()
        if last:
            out.append(last)
    return out


# CLI for quick smoke test
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--ingest-npa", type=Path)
    parser.add_argument("--gap", action="store_true")
    parser.add_argument("--trend", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    j = JUDB()
    if args.init:
        j.init_schema()
    if args.ingest_npa:
        j.ingest_npa_stalking_jsonl(args.ingest_npa)
    if args.gap:
        for row in j.gap_coefficient():
            print(row)
    if args.trend:
        for row in j.national_trend():
            print(row)
