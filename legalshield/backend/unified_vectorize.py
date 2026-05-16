"""Tag and vectorize ALL important LegalShield knowledge for fast semantic search.

Sources vectorized:
  - e-LAWS national laws (623k chunks) → already has vectors
  - Precedents (724k) → already in LanceDB
  - Bar associations (50 prefectural bars)
  - Support centers (33 seed + crawled)
  - NGOs (41 seed)
  - Prefecture resource scores (47)
  - Public facilities (courts, prosecutors, police, etc.)
  - e-Stat dataset metadata (885 tables)

Output: unified_knowledge.parquet with (text, source_type, tags, vector)
"""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
SEEDS = KNOWLEDGE / "seeds"
OUT = KNOWLEDGE / "unified_knowledge.parquet"


def load_seed_csv(name: str, source_type: str, tags: list[str], text_cols: list[str]) -> list[dict]:
    path = SEEDS / name
    if not path.exists():
        print(f"[skip] {path} not found")
        return []
    records = []
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            texts = [row.get(c, "") for c in text_cols if row.get(c)]
            if texts:
                records.append({
                    "text": " | ".join(texts),
                    "source_type": source_type,
                    "tags": ",".join(tags),
                })
    print(f"[ok] {name}: {len(records)} records")
    return records


def main() -> None:
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print(f"[init] model dim={model.get_embedding_dimension()}")

    all_records = []

    # 1. Bar associations
    all_records.extend(load_seed_csv(
        "bar_associations.csv", "bar_association",
        ["法律", "弁護士", "司法", "法律相談"],
        ["prefecture", "name", "phone"],
    ))

    # 2. Support centers
    all_records.extend(load_seed_csv(
        "support_centers_seed.csv", "support_center",
        ["支援", "相談", "DV", "性暴力", "児童", "家族"],
        ["type", "name", "prefecture", "address", "phone"],
    ))

    # 3. NGOs
    all_records.extend(load_seed_csv(
        "ngo_seed.csv", "ngo",
        ["NPO", "支援", "相談", "犯罪被害者", "DV", "児童"],
        ["name", "prefecture", "category", "notes"],
    ))

    # 4. Prefecture resources
    all_records.extend(load_seed_csv(
        "pref_resources.csv", "prefecture_resource",
        ["都道府県", "資源", "弁護士", "法律"],
        ["prefecture", "lawyers", "courts", "support_centers"],
    ))

    # 5. e-Stat dataset inventory (from DATA_INVENTORY.txt or directory listing)
    parsed_dir = KNOWLEDGE / "parsed"
    if parsed_dir.exists():
        for d in sorted(parsed_dir.iterdir()):
            if d.is_dir() and not d.name.endswith("_catalog"):
                n = len(list(d.glob("*.parquet")))
                all_records.append({
                    "text": f"e-Stat dataset {d.name}: {n} tables. Japanese government statistics.",
                    "source_type": "estat_dataset",
                    "tags": "統計,e-Stat,政府データ",
                })
        print(f"[ok] e-Stat datasets: {len([r for r in all_records if r['source_type']=='estat_dataset'])} records")

    # 6. elaws metadata (law names only, not full chunks)
    elaws_chunks = KNOWLEDGE / "elaws_full_chunks.parquet"
    if elaws_chunks.exists():
        df = pd.read_parquet(elaws_chunks, columns=["law_id", "law_name"])
        unique_laws = df.drop_duplicates("law_id")
        for _, row in unique_laws.iterrows():
            all_records.append({
                "text": f"日本国法 {row['law_name']} (ID: {row['law_id']})。全国適用の法律・政令・省令。",
                "source_type": "national_law",
                "tags": "国法,法律,e-LAWS,全国",
            })
        print(f"[ok] elaws metadata: {len(unique_laws)} unique laws")

    total = len(all_records)
    print(f"\n[init] total records to vectorize: {total}")

    # Embed all
    texts = [r["text"] for r in all_records]
    vectors = []
    batch = 256
    for i in range(0, total, batch):
        embs = model.encode(texts[i : i + batch], show_progress_bar=False, convert_to_numpy=True)
        vectors.extend(embs.tolist())
        if i % 2000 < batch:
            print(f"embedded {min(i+batch, total)}/{total}")

    for r, v in zip(all_records, vectors):
        r["vector"] = v

    df = pd.DataFrame(all_records)
    df.to_parquet(OUT)
    print(f"\n[ok] wrote {OUT}")
    print(f"     rows={len(df)}  cols={list(df.columns)}")
    print(f"     size={OUT.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
