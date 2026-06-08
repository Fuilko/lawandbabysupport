"""LanceDB → pgvector ETL（Phase B 移行スクリプト）

3 つの table（precedents / elaws_v2 / litigation）を pgvector に移植する。
再開可能（etl_progress を参照）、バッチ COPY ベース。

使い方:
    # pgvector 起動済みであること:
    #   docker compose -f infra/docker-compose.pgvector.yml up -d

    python scripts/lance_to_pgvector.py --table precedents --batch 5000
    python scripts/lance_to_pgvector.py --table elaws_v2 --batch 5000
    python scripts/lance_to_pgvector.py --table litigation --batch 5000

    # 全部一括:
    python scripts/lance_to_pgvector.py --all

ETL 完了後:
    python scripts/lance_to_pgvector.py --build-index
        # HNSW 索引を CREATE する（INSERT 完了後の方が速い）

設計メモ:
    * INSERT より COPY FROM STDIN (binary 不使用、テキスト形式) の方が pgvector に対し速い
    * embedding は "[0.1,0.2,...]" 形式の文字列で COPY できる
    * バッチ間 commit、失敗時は etl_progress.last_offset から再開
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import time
from pathlib import Path
from typing import Iterable

import lancedb
import psycopg
from psycopg import sql

# ---- 設定 ----
LANCE_DB_PATH = Path(os.environ.get(
    "LEGALSHIELD_LANCEDB", r"D:\projects\LegalShield\lancedb"
))
PG_DSN = os.environ.get(
    "LEGALSHIELD_PG_DSN",
    "host=localhost port=5435 dbname=legalshield user=legalshield password=legalshield_dev",
)

# (lance_table_name, pg_table_name, [(lance_col, pg_col), ...], embedding_col)
TABLE_MAP: dict[str, tuple[str, list[tuple[str, str]], str]] = {
    "precedents": (
        "precedents",
        [
            ("lawsuit_id", "lawsuit_id"),
            ("case_number", "case_number"),
            ("case_name", "case_name"),
            ("court_name", "court_name"),
            ("trial_type", "trial_type"),
            ("era", "era"),
            ("year", "year"),
            ("month", "month"),
            ("day", "day"),
            ("chunk_index", "chunk_index"),
            ("text", "text"),
            ("detail_link", "detail_link"),
            ("pdf_link", "pdf_link"),
            ("text_source", "text_source"),
        ],
        "vector",
    ),
    "elaws_v2": (
        "statutes",
        [
            ("law_id", "law_id"),
            ("law_name", "law_name"),
            ("article", "article"),
            ("text", "text"),
        ],
        "vector",
    ),
    "litigation": (
        "litigation",
        [
            ("chunk_id", "chunk_id"),
            ("source_type", "source_type"),
            ("source_id", "source_id"),
            ("chunk_idx", "chunk_idx"),
            ("category", "category"),
            ("title", "title"),
            ("source_url", "source_url"),
            ("text", "text"),
        ],
        "vector",
    ),
}


def _vec_to_pgliteral(v) -> str:
    """numpy/list → '[0.1,0.2,...]' 文字列。pgvector COPY 形式。"""
    return "[" + ",".join(f"{float(x):.7g}" for x in v) + "]"


def _escape_copy(s) -> str:
    """COPY text 形式のエスケープ（タブ・改行・バックスラッシュ）。"""
    if s is None:
        return r"\N"
    s = str(s)
    # PostgreSQL TEXT は NUL バイト不可 → 除去
    if "\x00" in s:
        s = s.replace("\x00", "")
    return (
        s.replace("\\", "\\\\")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def _resume_offset(conn, lance_table: str) -> int:
    cur = conn.execute(
        "SELECT last_offset FROM etl_progress WHERE table_name=%s",
        (lance_table,),
    )
    row = cur.fetchone()
    return int(row[0]) if row else 0


def _save_progress(conn, lance_table: str, offset: int, total: int, started_at):
    conn.execute(
        """
        INSERT INTO etl_progress(table_name, last_offset, total_expected, started_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT(table_name) DO UPDATE SET
            last_offset = EXCLUDED.last_offset,
            total_expected = EXCLUDED.total_expected
        """,
        (lance_table, offset, total, started_at),
    )


def _mark_finished(conn, lance_table: str):
    conn.execute(
        "UPDATE etl_progress SET finished_at=NOW() WHERE table_name=%s",
        (lance_table,),
    )


def migrate_table(lance_table: str, batch: int = 5000, limit: int | None = None) -> None:
    if lance_table not in TABLE_MAP:
        raise SystemExit(f"unknown table {lance_table}; choices={list(TABLE_MAP)}")
    pg_table, col_map, vec_col = TABLE_MAP[lance_table]

    print(f"[ETL] {lance_table} → {pg_table}  batch={batch}")
    db = lancedb.connect(str(LANCE_DB_PATH))
    if lance_table not in list(db.table_names()):
        raise SystemExit(f"lance table {lance_table} not found in {LANCE_DB_PATH}")
    tbl = db.open_table(lance_table)
    total = tbl.count_rows()
    print(f"[ETL] total rows in lance: {total:,}")
    if limit:
        total = min(total, limit)

    conn = psycopg.connect(PG_DSN, autocommit=False)
    try:
        offset = _resume_offset(conn, lance_table)
        if offset:
            print(f"[ETL] resuming from offset {offset:,}")
        started_at = "NOW()"
        # full load: pandas iterate via to_pandas() の chunk は LanceDB 0.x ではサポートされない場合あり
        # → pyarrow scanner を使う
        scanner = tbl.to_lance().scanner(batch_size=batch)
        seen = 0
        copied = 0
        pg_cols = [c[1] for c in col_map] + ["embedding"]
        copy_sql = sql.SQL("COPY {} ({}) FROM STDIN").format(
            sql.Identifier(pg_table),
            sql.SQL(",").join(sql.Identifier(c) for c in pg_cols),
        )
        t0 = time.time()
        for record_batch in scanner.to_batches():
            df = record_batch.to_pandas()
            if seen + len(df) <= offset:
                seen += len(df)
                continue
            if seen < offset:
                df = df.iloc[offset - seen :]
                seen = offset
            with conn.cursor().copy(copy_sql) as cp:
                for _, row in df.iterrows():
                    fields = []
                    for lance_col, _pg in col_map:
                        v = row.get(lance_col)
                        # pandas NaN 対策
                        try:
                            import math
                            if isinstance(v, float) and math.isnan(v):
                                v = None
                        except Exception:
                            pass
                        fields.append(_escape_copy(v))
                    vec = row[vec_col]
                    fields.append(_vec_to_pgliteral(vec))
                    cp.write("\t".join(fields) + "\n")
            seen += len(df)
            copied += len(df)
            _save_progress(conn, lance_table, seen, total, started_at)
            conn.commit()
            elapsed = time.time() - t0
            rate = copied / elapsed if elapsed > 0 else 0
            eta = (total - seen) / rate if rate > 0 else float("inf")
            print(
                f"[ETL] {lance_table}: {seen:,}/{total:,} "
                f"({100*seen/total:.1f}%)  rate={rate:.0f}/s  eta={eta/60:.1f}min"
            )
            if limit and seen >= limit:
                break
        _mark_finished(conn, lance_table)
        conn.commit()
        print(f"[ETL] {lance_table}: done in {(time.time()-t0)/60:.1f} min")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


HNSW_SQL = {
    "precedents": """
        CREATE INDEX IF NOT EXISTS idx_precedents_embedding
        ON precedents USING hnsw (embedding vector_cosine_ops)
        WITH (m=16, ef_construction=64);
    """,
    "statutes": """
        CREATE INDEX IF NOT EXISTS idx_statutes_embedding
        ON statutes USING hnsw (embedding vector_cosine_ops)
        WITH (m=16, ef_construction=64);
    """,
    "litigation": """
        CREATE INDEX IF NOT EXISTS idx_litigation_embedding
        ON litigation USING hnsw (embedding vector_cosine_ops)
        WITH (m=16, ef_construction=64);
    """,
}


def build_indexes(only: str | None = None) -> None:
    conn = psycopg.connect(PG_DSN, autocommit=True)
    try:
        for name, ddl in HNSW_SQL.items():
            if only and only != name:
                continue
            print(f"[INDEX] building HNSW on {name} (大量データだと数分〜数十分かかる)...")
            t0 = time.time()
            conn.execute(ddl)
            print(f"[INDEX] {name} done in {(time.time()-t0)/60:.1f} min")
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", choices=list(TABLE_MAP.keys()))
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--batch", type=int, default=5000)
    ap.add_argument("--limit", type=int, default=None, help="dev/smoke 用の上限")
    ap.add_argument("--build-index", action="store_true")
    args = ap.parse_args()

    if args.build_index:
        build_indexes()
        return
    if args.all:
        for t in TABLE_MAP:
            migrate_table(t, batch=args.batch, limit=args.limit)
        return
    if not args.table:
        ap.error("--table or --all required")
    migrate_table(args.table, batch=args.batch, limit=args.limit)


if __name__ == "__main__":
    main()
