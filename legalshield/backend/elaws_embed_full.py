"""Full embedding of ALL valid e-LAWS XML (7,800+ files) into Parquet.

Parquet is reliable on Windows; LanceDB will be rebuilt from Parquet.
Also writes chunked text for tag/vector indexing.
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
from sentence_transformers import SentenceTransformer

from legalshield.backend.elaws_embed import extract_law_text, _text_chunks, _is_valid_xml

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "knowledge" / "raw" / "elaws" / "lawdata"
OUT = ROOT / "knowledge"


def main() -> None:
    model = SentenceTransformer("all-MiniLM-L6-v2")
    dim = model.get_embedding_dimension()
    print(f"[init] model dim={dim}")

    files = [f for f in sorted(RAW_DIR.glob("*.xml")) if _is_valid_xml(f)]
    print(f"[init] valid XML files: {len(files)}")

    records = []
    t0 = time.time()
    for i, f in enumerate(files, 1):
        try:
            law_id, law_name, articles = extract_law_text(f)
            for art_num, art_text in articles:
                for chunk in _text_chunks(art_text):
                    records.append({
                        "law_id": law_id,
                        "law_name": law_name,
                        "article": art_num,
                        "text": chunk,
                    })
        except Exception:
            pass
        if i % 500 == 0:
            print(f"parsed {i}/{len(files)}  records={len(records)}  elapsed={time.time()-t0:.0f}s")

    total = len(records)
    print(f"[parse] total text chunks: {total}  elapsed={time.time()-t0:.0f}s")

    # Embed in batches
    vectors = []
    batch = 256
    for i in range(0, total, batch):
        texts = [r["text"] for r in records[i : i + batch]]
        embs = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        vectors.extend(embs.tolist())
        if (i + batch) % 5000 < batch:
            print(f"embedded {min(i+batch, total)}/{total}  elapsed={time.time()-t0:.0f}s")

    for r, v in zip(records, vectors):
        r["vector"] = v

    print(f"[embed] done in {time.time()-t0:.0f}s")

    # Write to Parquet (reliable on Windows)
    df = pd.DataFrame(records)
    out = OUT / "elaws_full_embedded.parquet"
    df.to_parquet(out)
    print(f"[ok] {out}  rows={len(df)}  cols={list(df.columns)}")

    # Also write plain chunks without vectors for inspection
    df_plain = df[["law_id", "law_name", "article", "text"]].copy()
    out2 = OUT / "elaws_full_chunks.parquet"
    df_plain.to_parquet(out2)
    print(f"[ok] {out2}  rows={len(df_plain)}")


if __name__ == "__main__":
    main()
