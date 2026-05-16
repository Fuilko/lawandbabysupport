"""Initialize / load the unified DuckDB database that joins
precedents (LanceDB), official statistics (Parquet), and case templates.

Usage:
    python -m legalshield.backend.unified_db init
    python -m legalshield.backend.unified_db load --dataset estat
    python -m legalshield.backend.unified_db query "SELECT count(*) FROM crime_stats"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]              # legalshield/
KNOWLEDGE = ROOT / "knowledge"
DUCKDB_PATH = KNOWLEDGE / "unified.duckdb"
PARSED = KNOWLEDGE / "parsed"

SCHEMA_SQL = """
-- 判例（LanceDB と並行：ここはメタデータと統計用の縮約版）
CREATE TABLE IF NOT EXISTS precedents_meta (
    lawsuit_id      VARCHAR,
    case_number     VARCHAR,
    court           VARCHAR,
    decided_on      DATE,
    case_type       VARCHAR,        -- 民事/刑事/行政/家事
    summary         TEXT,
    text_source     VARCHAR,        -- contents / gist / metadata
    PRIMARY KEY (lawsuit_id)
);

-- 犯罪統計（年×都道府県×罪種）
CREATE TABLE IF NOT EXISTS crime_stats (
    year            INTEGER,
    prefecture      VARCHAR,
    offense         VARCHAR,
    recognized      INTEGER,        -- 認知件数
    cleared         INTEGER,        -- 検挙件数
    prosecuted      INTEGER,        -- 起訴件数
    source          VARCHAR,        -- npa / kensatsu / saikousai
    fetched_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 司法統計（民事訴訟・調停・ADR等）
CREATE TABLE IF NOT EXISTS judicial_stats (
    year            INTEGER,
    court           VARCHAR,
    procedure       VARCHAR,        -- 通常訴訟/少額/調停/ADR/家事
    new_cases       INTEGER,
    disposed        INTEGER,
    avg_months      DOUBLE,
    source          VARCHAR,
    fetched_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 行政相談・救済統計
CREATE TABLE IF NOT EXISTS admin_stats (
    year            INTEGER,
    prefecture      VARCHAR,
    category        VARCHAR,        -- DV/児童虐待/高齢者虐待/消費者/労働/差別
    consultations   INTEGER,
    resolved        INTEGER,
    source          VARCHAR,
    fetched_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- NPO・支援団体
CREATE TABLE IF NOT EXISTS ngo_referrals (
    name            VARCHAR,
    prefecture      VARCHAR,
    category        VARCHAR,        -- 性暴力/DV/詐欺/外国人/障害者/高齢者/子ども
    phone           VARCHAR,
    url             VARCHAR,
    notes           TEXT,
    is_24h          BOOLEAN
);

-- 救済手続テンプレ（警察迂回ルート含む）
CREATE TABLE IF NOT EXISTS procedures (
    code            VARCHAR PRIMARY KEY,
    title           VARCHAR,
    target_harm     VARCHAR,        -- 性暴力/詐欺/DV/行政不作為/製品事故/...
    bypass_police   BOOLEAN,
    success_rate    DOUBLE,
    avg_days        INTEGER,
    avg_cost_jpy    INTEGER,
    burden_score    INTEGER,        -- 1-5 (psychological burden)
    docs_required   TEXT,
    citations       TEXT
);

-- 個人ケース（匿名化、自分のADR含む）
CREATE TABLE IF NOT EXISTS user_cases (
    case_id         VARCHAR PRIMARY KEY,
    user_pseudonym  VARCHAR,
    harm_type       VARCHAR,
    status          VARCHAR,        -- intake/evidence/filing/ongoing/closed
    started_on      DATE,
    summary         TEXT,
    next_step       VARCHAR
);

-- 監査ログ（証拠保全エンジン）
CREATE TABLE IF NOT EXISTS audit_log (
    ts              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actor           VARCHAR,
    action          VARCHAR,
    target          VARCHAR,
    sha256          VARCHAR,
    note            TEXT
);
"""


def init_db() -> None:
    KNOWLEDGE.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DUCKDB_PATH))
    con.execute(SCHEMA_SQL)
    print(f"[ok] initialized {DUCKDB_PATH}")
    for row in con.execute("SHOW TABLES").fetchall():
        print(" -", row[0])


def load_dataset(dataset: str) -> None:
    """Load all parquet files under knowledge/parsed/<dataset>/ as a view."""
    src = PARSED / dataset
    if not src.exists():
        sys.exit(f"no parquet directory: {src}")
    pattern = str(src / "*.parquet").replace("\\", "/")
    con = duckdb.connect(str(DUCKDB_PATH))
    con.execute(
        f"CREATE OR REPLACE VIEW {dataset}_raw AS SELECT * FROM read_parquet('{pattern}')"
    )
    n = con.execute(f"SELECT count(*) FROM {dataset}_raw").fetchone()[0]
    print(f"[ok] view {dataset}_raw rows={n}")


def query(sql: str) -> None:
    con = duckdb.connect(str(DUCKDB_PATH))
    df = con.execute(sql).fetchdf()
    print(df.to_string())


def main() -> None:
    p = argparse.ArgumentParser(description="LegalShield unified DuckDB")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    pl = sub.add_parser("load")
    pl.add_argument("--dataset", required=True)
    pq = sub.add_parser("query")
    pq.add_argument("sql")
    args = p.parse_args()
    if args.cmd == "init":
        init_db()
    elif args.cmd == "load":
        load_dataset(args.dataset)
    elif args.cmd == "query":
        query(args.sql)


if __name__ == "__main__":
    main()
