"""e-LAWS XML → pgvector statutes table（直接 ingest、LanceDB スキップ）

embed: multilingual-e5-small (384 dim、existing precedents と同モデル) + 'passage: ' 接頭辞。
書込み: pgvector statutes（id, law_id, law_name, article, text, embedding）。

使い方:
    # 既存の dummy 100 行を消したい場合:
    docker exec legalshield_pgvector_dev psql -U legalshield -d legalshield -c "TRUNCATE statutes RESTART IDENTITY;"

    python scripts/elaws_ingest_to_pgvector.py --batch 256
    # ETA: ~30-60min on RTX4080, ~120min on CPU (~600k chunks)

完了後 HNSW 再構築:
    docker exec legalshield_pgvector_dev psql -U legalshield -d legalshield \
        -c "REINDEX INDEX idx_statutes_embedding;"
    # （または DROP + CREATE）
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import time
from pathlib import Path

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legalshield.backend.elaws_embed import (  # noqa: E402
    extract_law_text, _text_chunks,
)

RAW_DIR = ROOT / "legalshield" / "knowledge" / "raw" / "elaws" / "lawdata"
PG_DSN = os.environ.get(
    "LEGALSHIELD_PG_DSN",
    "host=localhost port=5435 dbname=legalshield user=legalshield password=legalshield_dev",
)


def _vec_lit(v) -> str:
    return "[" + ",".join(f"{float(x):.7g}" for x in v) + "]"


def _esc(s) -> str:
    if s is None:
        return r"\N"
    s = str(s).replace("\x00", "")
    return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=256, help="embedding batch size")
    ap.add_argument("--limit-files", type=int, default=0)
    ap.add_argument("--commit-every", type=int, default=2000)
    args = ap.parse_args()

    if not RAW_DIR.exists():
        raise SystemExit(f"raw dir not found: {RAW_DIR}; run elaws_download.py first")

    files = sorted(RAW_DIR.glob("*.xml"))
    if args.limit_files:
        files = files[: args.limit_files]
    print(f"[init] xml files: {len(files)}")

    print("[init] loading sentence-transformers (multilingual-e5-small)...")
    from sentence_transformers import SentenceTransformer
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer("intfloat/multilingual-e5-small", device=device)
    # 文字長制限（一部の超長 article が VRAM を食い潰す対策）
    model.max_seq_length = 512
    print(f"[init] device={device}  dim={model.get_embedding_dimension()}  max_seq=512")

    conn = psycopg.connect(PG_DSN, autocommit=False)
    copy_sql = sql.SQL(
        "COPY statutes (law_id, law_name, article, text, embedding) FROM STDIN"
    )

    total_chunks = 0
    parse_fail = 0
    t0 = time.time()
    pending: list[tuple[str, str, str, str]] = []  # (law_id, law_name, article, text)

    def flush(pending_local):
        nonlocal total_chunks
        if not pending_local:
            return
        # 大量チャンクをサブバッチで処理して VRAM 蓄積を防ぐ
        sub_batch = args.batch
        embeds_all = []
        for i in range(0, len(pending_local), sub_batch):
            sub = pending_local[i : i + sub_batch]
            texts = [f"passage: {p[3]}" for p in sub]
            with torch.inference_mode():  # autograd 無効化で VRAM 節約
                embs = model.encode(
                    texts,
                    normalize_embeddings=True,
                    batch_size=sub_batch,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                )
            embeds_all.extend(embs)
        # 蓄積した cache を解放
        if device == "cuda":
            torch.cuda.empty_cache()
        with conn.cursor().copy(copy_sql) as cp:
            for (lid, lname, art, txt), v in zip(pending_local, embeds_all):
                row = "\t".join([_esc(lid), _esc(lname), _esc(art), _esc(txt), _vec_lit(v)]) + "\n"
                cp.write(row)
        conn.commit()
        total_chunks += len(pending_local)

    for fi, f in enumerate(files, 1):
        try:
            law_id, law_name, articles = extract_law_text(f)
        except Exception as e:
            parse_fail += 1
            continue
        for art_num, art_text in articles:
            for chunk in _text_chunks(art_text):
                if not chunk.strip():
                    continue
                pending.append((law_id, law_name, art_num, chunk))
                if len(pending) >= args.commit_every:
                    flush(pending)
                    pending = []
                    el = time.time() - t0
                    rate = total_chunks / el if el else 0
                    print(f"[prog] file {fi}/{len(files)}  chunks={total_chunks:,}  "
                          f"rate={rate:.0f}/s  parse_fail={parse_fail}  el={el/60:.1f}min")
    if pending:
        flush(pending)
    conn.close()
    print(f"[done] total chunks: {total_chunks:,}  parse_fail={parse_fail}  "
          f"elapsed={(time.time()-t0)/60:.1f}min")


if __name__ == "__main__":
    main()
