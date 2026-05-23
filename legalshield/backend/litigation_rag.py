"""
Litigation RAG Query CLI
========================

`litigation.lance` (CALL4 + 裁判所書式) を対象としたシンプルな RAG 検索 CLI。

使い方:
  python -m legalshield.backend.litigation_rag "答弁書の書き方を教えて"
  python -m legalshield.backend.litigation_rag "売買契約 債務不履行 損害賠償" --topk 8
  python -m legalshield.backend.litigation_rag --source court_form "請求の認否"
  python -m legalshield.backend.litigation_rag --source call4 "同性婚 違憲"

オプション:
  --topk N           上位 N 件を返す（既定: 5）
  --source TYPE      'call4' / 'court_form' / 'all'（既定: 'all'）
  --category C       カテゴリ部分一致フィルタ
  --show-text        全文を表示（既定: 200 字まで）
"""
from __future__ import annotations

import argparse
import sys
import io
from pathlib import Path

# Force UTF-8 stdout on Windows for Japanese display
if sys.platform.startswith("win"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parents[2]
LANCE_DIR = REPO_ROOT / "lancedb"
TABLE_NAME = "litigation"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def search(
    query: str,
    topk: int = 5,
    source: str = "all",
    category: str | None = None,
    show_full: bool = False,
) -> None:
    import lancedb
    from fastembed import TextEmbedding

    db = lancedb.connect(str(LANCE_DIR))
    if TABLE_NAME not in db.table_names():
        print(f"ERROR: Table '{TABLE_NAME}' not found. Run vectorize first.")
        sys.exit(1)
    tbl = db.open_table(TABLE_NAME)

    model = TextEmbedding(MODEL_NAME)
    qvec = list(model.embed([query]))[0]

    q = tbl.search(qvec).limit(topk * 3)  # over-fetch for filtering
    df = q.to_pandas()

    if source != "all":
        df = df[df["source_type"] == source]
    if category:
        df = df[df["category"].fillna("").str.contains(category, na=False)]
    df = df.head(topk)

    print("=" * 72)
    print(f"Query: {query}")
    print(f"  filters: source={source}, category={category}, topk={topk}")
    print(f"  total candidates in index: {tbl.count_rows():,}")
    print("=" * 72)
    if df.empty:
        print("(no matches)")
        return

    for i, row in df.reset_index(drop=True).iterrows():
        dist = float(row.get("_distance", 0.0))
        title = (row["title"] or "")[:60]
        text = row["text"] or ""
        snippet = text if show_full else (text[:240] + ("…" if len(text) > 240 else ""))
        snippet = snippet.replace("\n", " ")
        print()
        print(f"#{i+1}  [{row['source_type']}/{row['source_id']}]  distance={dist:.3f}")
        print(f"     カテゴリ: {row.get('category', '')}")
        print(f"     タイトル: {title}")
        print(f"     URL: {row.get('source_url', '')}")
        print(f"     抜粋: {snippet}")


def main() -> None:
    p = argparse.ArgumentParser(description="Litigation RAG Query CLI")
    p.add_argument("query", nargs="+", help="検索クエリ（日本語可）")
    p.add_argument("--topk", type=int, default=5)
    p.add_argument("--source", choices=("all", "call4", "court_form"), default="all")
    p.add_argument("--category", default=None)
    p.add_argument("--show-text", action="store_true", help="抜粋ではなく全文を表示")
    args = p.parse_args()
    query = " ".join(args.query)
    search(
        query,
        topk=args.topk,
        source=args.source,
        category=args.category,
        show_full=args.show_text,
    )


if __name__ == "__main__":
    main()
