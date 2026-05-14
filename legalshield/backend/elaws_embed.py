"""Ingest all 8,975 national laws into LanceDB for unified RAG with 71k precedents.

Steps:
  1. Parse each e-LAWS XML → extract law name + article-level text
  2. Chunk into ~500-token segments
  3. Embed with sentence-transformers (all-MiniLM-L6-v2, local)
  4. Write to LanceDB table 'elaws' with metadata (law_id, law_name, article_no)

NOTE: This is CPU-intensive. 8,975 laws × ~50 articles ≈ 450k chunks.
With MiniLM, ~100 chunks/sec on a modern CPU → ~75 min.
"""
from __future__ import annotations

import argparse
import html
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator

from lancedb import connect
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "knowledge" / "raw" / "elaws" / "lawdata"
DB_URI = ROOT / "lancedb"

CHUNK_SIZE = 500  # chars, rough proxy for tokens
CHUNK_OVERLAP = 100


def _text_chunks(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
        if start >= len(text):
            break
    return chunks


def extract_law_text(xml_path: Path) -> tuple[str, str, list[tuple[str, str]]]:
    """Returns (law_id, law_name, [(article_num, text), ...])."""
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        # Some files may have encoding issues; try reading as text
        text = xml_path.read_text(encoding="utf-8", errors="ignore")
        # Extract LawTitle and basic body text with regex fallback
        import re
        title = re.search(r'<LawTitle>([^<]+)</LawTitle>', text)
        law_name = title.group(1) if title else xml_path.stem
        body = re.sub(r'<[^>]+>', ' ', text)
        body = html.unescape(body)
        return (xml_path.stem, law_name, [("all", body)])

    root = tree.getroot()
    ns = {"e": "http://laws.e-gov.go.jp/constitution/"}
    law_name = ""
    law_title = root.find(".//e:LawTitle", ns)
    if law_title is not None and law_title.text:
        law_name = law_title.text
    if not law_name:
        law_title2 = root.find(".//LawTitle")
        if law_title2 is not None and law_title2.text:
            law_name = law_title2.text
    if not law_name:
        law_name = xml_path.stem

    articles = []
    for art in root.iter("{http://laws.e-gov.go.jp/constitution/}Article"):
        num = art.get("Num", "?")
        paras = []
        for para in art.iter("{http://laws.e-gov.go.jp/constitution/}Paragraph"):
            for sent in para.iter("{http://laws.e-gov.go.jp/constitution/}Sentence"):
                if sent.text:
                    paras.append(sent.text)
        body = "\n".join(paras)
        if body:
            articles.append((num, body))

    # Fallback: if no namespace-matched articles, try plain tag names
    if not articles:
        for art in root.iter("Article"):
            num = art.get("Num", "?")
            paras = []
            for para in art.iter("Paragraph"):
                for sent in para.iter("Sentence"):
                    if sent.text:
                        paras.append(sent.text)
            body = "\n".join(paras)
            if body:
                articles.append((num, body))

    if not articles:
        # ultimate fallback: raw text of entire XML
        body = ET.tostring(root, encoding="unicode", method="text")
        articles = [("all", body)]

    return (xml_path.stem, law_name, articles)


def _is_valid_xml(path: Path) -> bool:
    try:
        with open(path, "rb") as fh:
            h = fh.read(80)
        return b"<?xml" in h or (b"<DataRoot" in h or b"<Law " in h)
    except Exception:
        return False


def stream_chunks(raw_dir: Path) -> Iterator[dict]:
    files = sorted(raw_dir.glob("*.xml"))
    valid = 0
    for f in files:
        if not _is_valid_xml(f):
            continue
        valid += 1
        law_id, law_name, articles = extract_law_text(f)
        for art_num, art_text in articles:
            for chunk in _text_chunks(art_text):
                yield {
                    "law_id": law_id,
                    "law_name": law_name,
                    "article": art_num,
                    "text": chunk,
                }
    print(f"[scan] valid XML files: {valid}/{len(files)}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="all-MiniLM-L6-v2")
    p.add_argument("--batch", type=int, default=128)
    p.add_argument("--limit", type=int, default=0, help="0 = all")
    args = p.parse_args()

    print(f"[init] loading model {args.model} ...")
    model = SentenceTransformer(args.model)
    dim = model.get_sentence_embedding_dimension()
    print(f"[init] embedding dim = {dim}")

    db = connect(str(DB_URI))
    # Open or create table using pyarrow schema
    try:
        tbl = db.open_table("elaws")
        print("[init] opened existing table 'elaws'")
    except Exception:
        import pyarrow as pa
        schema = pa.schema([
            pa.field("vector", pa.list_(pa.float32(), dim)),
            pa.field("law_id", pa.string()),
            pa.field("law_name", pa.string()),
            pa.field("article", pa.string()),
            pa.field("text", pa.string()),
        ])
        tbl = db.create_table("elaws", schema=schema)
        print("[init] created table 'elaws'")

    print("[init] scanning XML files ...")
    all_chunks = list(stream_chunks(RAW_DIR))
    if args.limit:
        all_chunks = all_chunks[: args.limit]
    print(f"[init] total chunks = {len(all_chunks)}")

    t0 = time.time()
    texts = [c["text"] for c in all_chunks]
    total = len(texts)
    processed = 0
    batch_size = args.batch
    for i in range(0, total, batch_size):
        batch_texts = texts[i : i + batch_size]
        batch_meta = all_chunks[i : i + batch_size]
        embs = model.encode(batch_texts, show_progress_bar=False, convert_to_numpy=True)
        records = []
        for emb, meta in zip(embs, batch_meta):
            records.append({
                "vector": emb.tolist(),
                "law_id": meta["law_id"],
                "law_name": meta["law_name"],
                "article": meta["article"],
                "text": meta["text"],
            })
        tbl.add(records)
        processed += len(batch_texts)
        if processed % 1000 == 0:
            el = time.time() - t0
            rate = processed / el if el else 0
            print(f"progress {processed}/{total}  rate={rate:.1f}/s")

    print(f"[done] processed {processed} chunks in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
