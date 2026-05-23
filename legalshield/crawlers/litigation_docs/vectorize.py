"""
Litigation Vector Indexer (LanceDB)
====================================

`litigation_chunks` (DuckDB) のテキスト全件を fastembed で 384 次元ベクトルに変換し、
LanceDB の `litigation.lance` テーブルに書き込む。

これにより:
  - 答辯書ドラフト生成のための RAG 検索が可能になる
  - CALL4 訴訟事例 + 裁判所書式 を同一空間で類似検索できる

モデル:
  sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
  (384 dim, ONNX 量子化版、日本語サポート、~120MB)

使い方:
  python -m legalshield.crawlers.litigation_docs.vectorize
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import duckdb
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = REPO_ROOT / "legalshield" / "lancedb" / "litigation.duckdb"
LANCE_DIR = REPO_ROOT / "lancedb"  # match existing convention
LANCE_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TABLE_NAME = "litigation"
BATCH = 64

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("vectorize")


def batched(seq: list, n: int) -> Iterable[list]:
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def run() -> dict:
    import lancedb
    from fastembed import TextEmbedding

    log.info("Loading chunks from DuckDB...")
    con = duckdb.connect(str(DB_PATH))
    df = con.execute(
        """
        SELECT chunk_id, source_type, source_id, chunk_idx,
               text, category, title, source_url
        FROM litigation_chunks
        WHERE LENGTH(text) > 30
        ORDER BY source_type, source_id, chunk_idx
        """
    ).df()
    con.close()
    log.info("  %d chunks loaded", len(df))

    log.info("Loading embedding model: %s", MODEL_NAME)
    model = TextEmbedding(MODEL_NAME)
    log.info("Embedding %d texts in batches of %d...", len(df), BATCH)

    texts = df["text"].tolist()
    vectors: list[np.ndarray] = []
    done = 0
    for chunk in batched(texts, BATCH):
        vecs = list(model.embed(chunk))
        vectors.extend(vecs)
        done += len(chunk)
        if done % (BATCH * 5) == 0 or done == len(texts):
            log.info("  embedded %d / %d", done, len(texts))

    df["vector"] = vectors
    log.info("Done embedding. Writing to LanceDB...")

    db = lancedb.connect(str(LANCE_DIR))
    if TABLE_NAME in db.table_names():
        db.drop_table(TABLE_NAME)
        log.info("  dropped existing table '%s'", TABLE_NAME)

    tbl = db.create_table(TABLE_NAME, data=df)
    log.info("  created table '%s' with %d rows", TABLE_NAME, tbl.count_rows())

    # Quick sanity-check search
    log.info("Sanity check: searching for '答弁書 書き方'...")
    qvec = list(model.embed(["答弁書 書き方"]))[0]
    hits = tbl.search(qvec).limit(5).to_pandas()
    for _, row in hits.iterrows():
        log.info(
            "  [%s/%s] %s  | %s",
            row["source_type"], row["source_id"],
            (row["title"] or "")[:50],
            (row["text"] or "")[:80].replace("\n", " "),
        )

    return {
        "table": TABLE_NAME,
        "rows": int(tbl.count_rows()),
        "dim": int(len(vectors[0])) if vectors else 0,
        "model": MODEL_NAME,
        "lance_dir": str(LANCE_DIR / f"{TABLE_NAME}.lance"),
    }


if __name__ == "__main__":
    summary = run()
    log.info("Done: %s", summary)
