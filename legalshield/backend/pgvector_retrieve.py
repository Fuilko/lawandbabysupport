"""pgvector 検索バックエンド（Phase B）

LanceDB と同等の retrieve 関数を pgvector で提供する。
api.py が RETRIEVE_BACKEND env で lance/pg を切り替えるための実装。

設計:
    * 既存 harness.Source の interface を維持
    * cosine 距離（embedding は normalize 済み = e5）
    * HNSW 索引が無い場合も動く（slow but correct）
    * connection pool は psycopg.ConnectionPool を使用（lazy init）
"""
from __future__ import annotations

import os
from typing import Optional

import psycopg
from psycopg_pool import ConnectionPool

from . import harness

PG_DSN = os.environ.get(
    "LEGALSHIELD_PG_DSN",
    "host=localhost port=5435 dbname=legalshield user=legalshield password=legalshield_dev",
)

_pool: Optional[ConnectionPool] = None


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(PG_DSN, min_size=1, max_size=4, open=True)
    return _pool


def _vec_literal(v: list[float]) -> str:
    return "[" + ",".join(f"{float(x):.7g}" for x in v) + "]"


def _exec_with_hnsw_fallback(conn, sql: str, params: tuple, k: int):
    """HNSW 索引で結果 < k なら sequential scan で fallback。
    HNSW graph が ef_construction 不足等で hole がある場合の保険。"""
    rows = list(conn.execute(sql, params))
    if len(rows) >= k:
        return rows
    # fallback: seq scan は遅いが完璧な recall
    try:
        conn.execute("SET LOCAL enable_indexscan = off")
        conn.execute("SET LOCAL enable_bitmapscan = off")
    except Exception:
        pass
    return list(conn.execute(sql, params))


def make_precedent_retriever(embed_query) -> harness.RetrieveFn:
    """precedents から cosine 距離で top-k 取得。lawsuit_id で dedupe。"""
    def _retrieve(question: str, k: int) -> list[harness.Source]:
        qvec = embed_query(question)
        sql = """
            SELECT
                lawsuit_id, case_number, case_name, court_name,
                trial_type, era, year, text,
                embedding <=> %s::vector AS distance
            FROM precedents
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        out: list[harness.Source] = []
        seen: set[str] = set()
        with _get_pool().connection() as conn:
            rows = _exec_with_hnsw_fallback(conn, sql, (_vec_literal(qvec), _vec_literal(qvec), k * 3), k)
            cur = iter(rows)
            for row in cur:
                lawsuit_id, case_number, case_name, court, trial, era, year, text, dist = row
                key = lawsuit_id or case_number or case_name or text[:50]
                if key in seen:
                    continue
                seen.add(key)
                out.append(harness.Source(
                    id="", kind="precedent", text=text or "",
                    score=float(dist),
                    trust="high", provenance="precedent_db_pg",
                    citation=case_number or court or "判例",
                    metadata={
                        "case_number": case_number, "court": court,
                        "trial_type": trial, "era": era, "year": year,
                    },
                ))
                if len(out) >= k:
                    break
        return out
    return _retrieve


def make_statute_retriever(embed_query) -> harness.RetrieveFn:
    def _retrieve(question: str, k: int) -> list[harness.Source]:
        qvec = embed_query(question)
        sql = """
            SELECT law_id, law_name, article, text,
                   embedding <=> %s::vector AS distance
            FROM statutes
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        out: list[harness.Source] = []
        with _get_pool().connection() as conn:
            rows = _exec_with_hnsw_fallback(conn, sql, (_vec_literal(qvec), _vec_literal(qvec), k), k)
            cur = iter(rows)
            for row in cur:
                law_id, law_name, article, text, dist = row
                citation = f"{law_name or ''} 第{article}条" if article else (law_name or "法令")
                out.append(harness.Source(
                    id="", kind="statute", text=text or "",
                    score=float(dist),
                    trust="high", provenance="statute_db_pg",
                    citation=citation,
                    metadata={"law_id": law_id, "law_name": law_name, "article": article},
                ))
        return out
    return _retrieve


def health_check() -> dict:
    """api.py /health で呼ぶ。"""
    try:
        with _get_pool().connection() as conn:
            cur = conn.execute(
                "SELECT (SELECT count(*) FROM precedents),"
                "       (SELECT count(*) FROM statutes),"
                "       (SELECT count(*) FROM litigation)"
            )
            p, s, l = cur.fetchone()
        return {"ok": True, "precedents": p, "statutes": s, "litigation": l}
    except Exception as e:
        return {"ok": False, "error": str(e)}
