"""
Full ingestion: 71,175 precedent cases → LanceDB vector store.
Windows version with CUDA GPU (RTX 4080).

Setup:
    pip install sentence-transformers lancedb pyarrow tqdm orjson torch --index-url https://download.pytorch.org/whl/cu124

Usage:
    python full_ingest_windows.py
"""
import time
from pathlib import Path

import lancedb
import orjson
import torch
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# ===== Windows paths - adjust as needed =====
DATA_DIR = Path("D:/projects/LegalShield/data_set")
LANCE_DB_PATH = Path("D:/projects/LegalShield/lancedb")
# =============================================

LANCE_DB_PATH.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 1024
CHUNK_OVERLAP = 128
BATCH_SIZE = 512  # RTX 4080 16GB VRAM can handle larger batches
TABLE_NAME = "precedents"


def chunk_text(text: str) -> list[str]:
    if len(text) <= CHUNK_SIZE:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + CHUNK_SIZE])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def _fmt_date(d: dict) -> str:
    if not isinstance(d, dict):
        return ""
    era = d.get("era", "")
    y = d.get("year", 0)
    m = d.get("month", 0)
    day = d.get("day", 0)
    if not (era or y):
        return ""
    return f"{era}{y}年{m}月{day}日"


def get_text_and_source(data: dict) -> tuple[str, str]:
    """Return (text, source_tier). Tier: 'contents' > 'gist' > 'metadata'."""
    # Tier A: full contents
    c = data.get("contents")
    if c and isinstance(c, str) and c.strip():
        return c, "contents"

    # Tier B: gist + case_gist (early-era precedents)
    parts = []
    g = data.get("gist")
    if g and isinstance(g, str) and g.strip():
        parts.append(f"【要旨】{g.strip()}")
    cg = data.get("case_gist")
    if cg and isinstance(cg, str) and cg.strip():
        parts.append(f"【裁判要旨】{cg.strip()}")
    if parts:
        return "\n\n".join(parts), "gist"

    # Tier C: metadata-only stub (synthesise searchable text)
    fields = []
    if data.get("case_name"):
        fields.append(f"【事件名】{data['case_name']}")
    if data.get("court_name"):
        fields.append(f"【裁判所】{data['court_name']}")
    dt = _fmt_date(data.get("date"))
    if dt:
        fields.append(f"【裁判日】{dt}")
    if data.get("trial_type"):
        fields.append(f"【審級】{data['trial_type']}")
    if data.get("result_type") or data.get("result"):
        fields.append(f"【結果】{data.get('result_type','')} {data.get('result','')}".strip())
    if data.get("ref_law"):
        fields.append(f"【参照法令】{data['ref_law']}")
    if data.get("article_info"):
        fields.append(f"【掚載】{data['article_info']}")
    if data.get("original_court_name"):
        odt = _fmt_date(data.get("original_date"))
        fields.append(f"【原裁判】{data['original_court_name']} {odt}".strip())
    if data.get("case_number"):
        fields.append(f"【事件番号】{data['case_number']}")
    if fields:
        return "\n".join(fields), "metadata"

    return "", "none"


def iter_all_precedents(base_path: Path):
    """Iterate all precedent JSON files across all decades."""
    precedent_dir = base_path / "precedent"
    for decade_dir in sorted(precedent_dir.iterdir()):
        if not decade_dir.is_dir():
            continue
        for json_file in sorted(decade_dir.iterdir()):
            if json_file.suffix != ".json" or json_file.name == "list.json":
                continue
            try:
                data = orjson.loads(json_file.read_bytes())
                text, source = get_text_and_source(data)
                if text:
                    data["_text"] = text
                    data["_text_source"] = source
                    yield data
            except Exception:
                continue


def main() -> None:
    print(f"{'='*60}")
    print(f"  LegalShield - Full Precedent Ingestion (Windows/CUDA)")
    print(f"  CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
        print(f"  VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    print(f"  Start: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer("intfloat/multilingual-e5-small", device=device)

    db = lancedb.connect(str(LANCE_DB_PATH))
    existing = db.table_names() if hasattr(db, 'table_names') else db.list_tables()
    if TABLE_NAME in existing:
        db.drop_table(TABLE_NAME)

    table = None
    batch: list[dict] = []
    total_cases = 0
    total_chunks = 0
    start_time = time.time()

    for case in tqdm(iter_all_precedents(DATA_DIR), desc="Cases", total=71175):
        date = case.get("date", {})
        meta = {
            "case_number": case.get("case_number", ""),
            "case_name": case.get("case_name", ""),
            "court_name": case.get("court_name", ""),
            "trial_type": case.get("trial_type", ""),
            "lawsuit_id": case.get("lawsuit_id", ""),
            "era": date.get("era", ""),
            "year": date.get("year", 0),
            "month": date.get("month", 0),
            "day": date.get("day", 0),
            "detail_link": case.get("detail_page_link", ""),
            "pdf_link": case.get("full_pdf_link", ""),
            "text_source": case.get("_text_source", "contents"),
        }

        for i, chunk in enumerate(chunk_text(case["_text"])):
            batch.append({"text": chunk, "chunk_index": i, **meta})

        total_cases += 1

        # Process batch
        if len(batch) >= BATCH_SIZE:
            texts = [f"passage: {r['text']}" for r in batch]
            embeddings = model.encode(texts, normalize_embeddings=True, batch_size=BATCH_SIZE)
            for rec, emb in zip(batch, embeddings):
                rec["vector"] = emb.tolist()

            if table is None:
                table = db.create_table(TABLE_NAME, batch)
            else:
                table.add(batch)

            total_chunks += len(batch)
            batch = []

            if total_cases % 1000 == 0:
                elapsed = time.time() - start_time
                speed = total_chunks / elapsed
                eta = (71175 - total_cases) * (elapsed / total_cases) / 60
                print(f"\n  📊 {total_cases} cases | {total_chunks} chunks | "
                      f"{speed:.0f} chunks/s | ETA: {eta:.0f} min")

    # Final batch
    if batch:
        texts = [f"passage: {r['text']}" for r in batch]
        embeddings = model.encode(texts, normalize_embeddings=True, batch_size=BATCH_SIZE)
        for rec, emb in zip(batch, embeddings):
            rec["vector"] = emb.tolist()
        if table is None:
            table = db.create_table(TABLE_NAME, batch)
        else:
            table.add(batch)
        total_chunks += len(batch)

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"  ✅ DONE")
    print(f"  Cases: {total_cases}")
    print(f"  Chunks: {total_chunks}")
    print(f"  Time: {elapsed/3600:.1f} hours")
    print(f"  Speed: {total_chunks/elapsed:.0f} chunks/sec")
    print(f"  DB path: {LANCE_DB_PATH}")
    print(f"  DB size: {sum(f.stat().st_size for f in LANCE_DB_PATH.rglob('*') if f.is_file()) / 1024**2:.0f} MB")
    print(f"  End: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
