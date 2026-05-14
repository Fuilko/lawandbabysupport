"""Ingest e-LAWS XML into LanceDB using pandas (reliable persist).
"""
from __future__ import annotations

import time
from pathlib import Path

import lancedb
import pandas as pd
from sentence_transformers import SentenceTransformer

from legalshield.backend.elaws_embed import extract_law_text, _text_chunks, _is_valid_xml

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "knowledge" / "raw" / "elaws" / "lawdata"
DB_URI = str(ROOT / "lancedb")


def main() -> None:
    model = SentenceTransformer("all-MiniLM-L6-v2")
    dim = model.get_embedding_dimension()
    print(f"[init] model dim={dim}")

    files = [f for f in sorted(RAW_DIR.glob("*.xml")) if _is_valid_xml(f)]
    print(f"[init] valid XML files: {len(files)}")

    all_records = []
    for f in files:
        law_id, law_name, articles = extract_law_text(f)
        for art_num, art_text in articles:
            for chunk in _text_chunks(art_text):
                all_records.append({
                    "law_id": law_id,
                    "law_name": law_name,
                    "article": art_num,
                    "text": chunk,
                })

    total = len(all_records)
    print(f"[init] total text chunks: {total}")

    # Embed in batches
    t0 = time.time()
    vectors = []
    batch = 256
    for i in range(0, total, batch):
        texts = [r["text"] for r in all_records[i : i + batch]]
        embs = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        vectors.extend(embs.tolist())
        if (i + batch) % 5000 < batch:
            print(f"embedded {min(i+batch, total)}/{total}  elapsed={time.time()-t0:.0f}s")

    for r, v in zip(all_records, vectors):
        r["vector"] = v

    print(f"[embed] done in {time.time()-t0:.0f}s")

    # Write to LanceDB via pandas
    db = lancedb.connect(DB_URI)
    # Drop old if exists
    for name in ("elaws", "elaws_v2"):
        try:
            db.drop_table(name)
            print(f"[db] dropped old '{name}'")
        except Exception:
            pass

    df = pd.DataFrame(all_records)
    tbl = db.create_table("elaws", data=df, mode="overwrite")
    print(f"[db] created 'elaws'  rows={tbl.count_rows()}")

    # Force flush for Windows persistence
    time.sleep(3)
    try:
        tbl.optimize()
        print("[db] optimize done")
    except Exception as e:
        print(f"[db] optimize skip: {e}")

    # Verify from fresh connection
    db2 = lancedb.connect(DB_URI)
    t2 = db2.open_table("elaws")
    print(f"[verify] persistent rows: {t2.count_rows()}")


if __name__ == "__main__":
    main()
