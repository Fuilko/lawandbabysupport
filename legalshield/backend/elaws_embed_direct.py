"""Direct embedding of valid e-LAWS XML files into LanceDB.

Simpler than elaws_embed.py: no argparse, no Tee-Object issues.
"""
from __future__ import annotations

import time
from pathlib import Path

import lancedb
import pyarrow as pa
from sentence_transformers import SentenceTransformer

from legalshield.backend.elaws_embed import extract_law_text, _text_chunks, _is_valid_xml

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "knowledge" / "raw" / "elaws" / "lawdata"
DB_URI = ROOT / "lancedb"


def main() -> None:
    model = SentenceTransformer("all-MiniLM-L6-v2")
    dim = model.get_embedding_dimension()
    print(f"[init] model dim={dim}")

    db = lancedb.connect(str(DB_URI))
    try:
        db.drop_table("elaws")
        print("[init] dropped old elaws table")
    except Exception:
        pass

    schema = pa.schema([
        pa.field("vector", pa.list_(pa.float32(), dim)),
        pa.field("law_id", pa.string()),
        pa.field("law_name", pa.string()),
        pa.field("article", pa.string()),
        pa.field("text", pa.string()),
    ])
    tbl = db.create_table("elaws", schema=schema)
    print("[init] created table 'elaws'")

    files = [f for f in sorted(RAW_DIR.glob("*.xml")) if _is_valid_xml(f)]
    print(f"[init] valid XML files: {len(files)}")

    batch_texts, batch_meta = [], []
    total_chunks = 0
    t0 = time.time()

    for f in files:
        law_id, law_name, articles = extract_law_text(f)
        for art_num, art_text in articles:
            for chunk in _text_chunks(art_text):
                batch_texts.append(chunk)
                batch_meta.append({"law_id": law_id, "law_name": law_name, "article": art_num, "text": chunk})
                if len(batch_texts) >= 128:
                    embs = model.encode(batch_texts, show_progress_bar=False, convert_to_numpy=True)
                    records = [{"vector": e.tolist(), **m} for e, m in zip(embs, batch_meta)]
                    tbl.add(records)
                    total_chunks += len(records)
                    batch_texts, batch_meta = [], []
                    if total_chunks % 10000 == 0:
                        print(f"progress {total_chunks}  elapsed={time.time()-t0:.0f}s")

    # Final batch
    if batch_texts:
        embs = model.encode(batch_texts, show_progress_bar=False, convert_to_numpy=True)
        records = [{"vector": e.tolist(), **m} for e, m in zip(embs, batch_meta)]
        tbl.add(records)
        total_chunks += len(records)

    elapsed = time.time() - t0
    print(f"[done] total_chunks={total_chunks}  elapsed={elapsed:.0f}s  rate={total_chunks/elapsed:.1f}/s")
    print(f"[verify] table rows: {tbl.count_rows()}")


if __name__ == "__main__":
    main()
