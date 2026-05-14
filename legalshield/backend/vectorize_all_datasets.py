"""Batch tag and vectorize ALL downloaded datasets for unified semantic search.

Sources:
  - e-Stat 885 tables (read metadata + sample rows → description text)
  - Facilities crawled data
  - Support center seeds
  - Bar association seeds
  - NGO seeds
  - Prefecture resource scores
  - National law metadata (already embedded separately)

Output: all_datasets_vectorized.parquet
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
PARSED = KNOWLEDGE / "parsed"
RAW = KNOWLEDGE / "raw"
OUT = KNOWLEDGE / "all_datasets_vectorized.parquet"


def describe_parquet(path: Path) -> str | None:
    """Generate a human-readable description of a Parquet file."""
    try:
        con = duckdb.connect()
        # Get columns
        info = con.execute(f"SELECT * FROM read_parquet('{str(path).replace(chr(92),'/')}') LIMIT 0").fetchdf()
        cols = list(info.columns)
        # Get row count (approximate from file size or sample)
        df = con.execute(f"SELECT * FROM read_parquet('{str(path).replace(chr(92),'/')}') LIMIT 3").fetchdf()
        row_hint = len(df)

        dataset_name = path.parent.name
        filename = path.stem

        # Build description
        parts = [f"e-Stat dataset '{dataset_name}' file '{filename}'"]
        parts.append(f"Columns: {', '.join(cols[:8])}")
        if len(cols) > 8:
            parts.append(f"...and {len(cols)-8} more columns")

        # Sample values from first row
        if not df.empty:
            sample_cols = [c for c in cols if c.lower() not in ('area_code','time_code','value')][:4]
            sample = []
            for c in sample_cols:
                v = str(df[c].iloc[0]) if c in df.columns else ""
                if v and v != "None":
                    sample.append(f"{c}={v[:40]}")
            if sample:
                parts.append(f"Sample: {' | '.join(sample)}")

        return "; ".join(parts)
    except Exception:
        return None


def vectorize_all() -> None:
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print(f"[init] model dim={model.get_embedding_dimension()}")

    records = []

    # 1. e-Stat parsed tables (sample from each dataset)
    if PARSED.exists():
        datasets = [d for d in PARSED.iterdir() if d.is_dir() and not d.name.endswith("_catalog")]
        print(f"[scan] {len(datasets)} e-Stat datasets")
        for d in datasets:
            files = list(d.glob("*.parquet"))
            if not files:
                continue
            # Pick representative file (not catalog, largest)
            rep = max([f for f in files if "catalog" not in f.name], key=lambda x: x.stat().st_size, default=None)
            if rep:
                desc = describe_parquet(rep)
                if desc:
                    records.append({
                        "text": desc,
                        "source_type": "estat_table",
                        "tags": f"e-Stat,{d.name},統計,政府データ",
                        "source_file": str(rep.relative_to(ROOT)),
                    })
            if len(records) % 100 == 0:
                print(f"  processed {len(records)} descriptions")

    # 2. Facilities raw data (if any HTML parsed)
    facilities_raw = RAW / "facilities"
    if facilities_raw.exists():
        for sub in facilities_raw.iterdir():
            if sub.is_dir():
                files = list(sub.glob("*.html"))
                records.append({
                    "text": f"Public facility data: {sub.name} ({len(files)} HTML files). Crawled from official sources.",
                    "source_type": "facility",
                    "tags": f"施設,{sub.name},公共インフラ",
                    "source_file": str(sub.relative_to(ROOT)),
                })

    # 3. Seeds (already in unified_knowledge but add more detail)
    seeds_dir = KNOWLEDGE / "seeds"
    for csv_file in seeds_dir.glob("*.csv"):
        try:
            df = pd.read_csv(csv_file, encoding="utf-8-sig")
            for _, row in df.iterrows():
                texts = [str(v) for v in row.values if pd.notna(v) and str(v).strip()]
                if texts:
                    records.append({
                        "text": f"{csv_file.stem}: {' | '.join(texts[:5])}",
                        "source_type": "seed",
                        "tags": f"seed,{csv_file.stem}",
                        "source_file": str(csv_file.relative_to(ROOT)),
                    })
        except Exception:
            pass

    total = len(records)
    print(f"\n[init] total records to vectorize: {total}")

    if total == 0:
        print("[warn] no records found")
        return

    # Embed
    texts = [r["text"] for r in records]
    vectors = []
    batch = 256
    for i in range(0, total, batch):
        embs = model.encode(texts[i : i + batch], show_progress_bar=False, convert_to_numpy=True)
        vectors.extend(embs.tolist())
        if (i + batch) % 1000 < batch:
            print(f"embedded {min(i+batch, total)}/{total}")

    for r, v in zip(records, vectors):
        r["vector"] = v

    df = pd.DataFrame(records)
    df.to_parquet(OUT)
    print(f"\n[ok] {OUT}")
    print(f"     rows={len(df)}  cols={list(df.columns)}")
    print(f"     size={OUT.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    vectorize_all()
