"""
LegalShield RAG CLI — Japanese Precedent Retrieval + LLM Answer

Usage:
  python rag_query.py "質問文をここに" [--k 8] [--model gemma3:27b]
  python rag_query.py --interactive
  python rag_query.py --retrieve-only "質問"          # skip LLM, just show top-K
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import lancedb
import requests
import torch
from sentence_transformers import SentenceTransformer

# --- Config ---
DB_PATH = Path(r"D:\projects\LegalShield\lancedb")
TABLE_NAME = "precedents"
EMBED_MODEL = "intfloat/multilingual-e5-small"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
DEFAULT_LLM = "gemma3:27b"
DEFAULT_K = 8

SYSTEM_PROMPT = """あなたは日本の法律実務に精通したアシスタントです。
提示された判例（最高裁判所・下級審）の抜粋を根拠に、ユーザーの法律質問に答えてください。

ルール:
1. 必ず提示された判例のみを根拠とし、判例外の知識で断定しない
2. 引用時は [事件番号] を末尾に付ける（例: 最判平成24年... [平成20(受)1234]）
3. 判例が質問と関連薄い場合は「直接的な判例は見当たらない」と明示
4. 結論 → 根拠判例 → 注意点 の順で構造化
5. 簡潔・実務的に。冗長な前置きは禁止"""


def embed_query(model: SentenceTransformer, text: str) -> list[float]:
    """e5 query convention: prefix 'query: '."""
    vec = model.encode([f"query: {text}"], normalize_embeddings=True)[0]
    return vec.tolist()


def retrieve(table, query_vec: list[float], k: int, *, dedupe_cases: bool = True) -> list[dict[str, Any]]:
    """Retrieve top-K chunks. With dedupe_cases=True, return K unique cases
    (over-fetch then keep best chunk per lawsuit_id)."""
    if not dedupe_cases:
        return table.search(query_vec).limit(k).to_list()
    # Over-fetch ~5x to ensure we have K unique cases
    raw = table.search(query_vec).limit(k * 5).to_list()
    seen: dict[str, dict[str, Any]] = {}
    for r in raw:
        key = str(r.get("lawsuit_id") or r.get("case_number"))
        if key not in seen:
            seen[key] = r
        if len(seen) >= k:
            break
    return list(seen.values())[:k]


def format_context(rows: list[dict[str, Any]]) -> str:
    """Build prompt context block. Group by case (lawsuit_id) so multi-chunk hits don't repeat headers."""
    seen_cases: dict[str, list[dict]] = {}
    order: list[str] = []
    for r in rows:
        key = str(r.get("lawsuit_id") or r.get("case_number"))
        if key not in seen_cases:
            seen_cases[key] = []
            order.append(key)
        seen_cases[key].append(r)

    blocks = []
    for i, key in enumerate(order, 1):
        chunks = seen_cases[key]
        head = chunks[0]
        era = head.get("era", "")
        y, m, d = head.get("year", 0), head.get("month", 0), head.get("day", 0)
        date_str = f"{era}{y}年{m}月{d}日" if era else ""
        cn = head.get("case_number", "")
        court = head.get("court_name", "")
        case_name = head.get("case_name", "")
        src = head.get("text_source", "contents")
        link = head.get("detail_link", "")
        body = "\n---\n".join(c.get("text", "") for c in chunks)
        blocks.append(
            f"【判例{i}】[{cn}] {court} {date_str}\n"
            f"事件名: {case_name}  (text_source={src})\n"
            f"link: {link}\n"
            f"{body}"
        )
    return "\n\n".join(blocks)


def call_ollama(model: str, system: str, user: str, *, stream: bool = True) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": stream,
        "options": {"temperature": 0.2, "num_ctx": 8192},
    }
    if stream:
        full = []
        with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=1800) as r:
            r.raise_for_status()
            import json as _json
            for line in r.iter_lines():
                if not line:
                    continue
                obj = _json.loads(line)
                tok = obj.get("message", {}).get("content", "")
                if tok:
                    print(tok, end="", flush=True)
                    full.append(tok)
                if obj.get("done"):
                    break
        print()
        return "".join(full)
    r = requests.post(OLLAMA_URL, json={**payload, "stream": False}, timeout=1800)
    r.raise_for_status()
    return r.json()["message"]["content"]


def run_query(
    table,
    embed_model: SentenceTransformer,
    question: str,
    k: int,
    llm_model: str,
    retrieve_only: bool = False,
) -> None:
    t0 = time.time()
    qvec = embed_query(embed_model, question)
    rows = retrieve(table, qvec, k)
    t_retrieve = time.time() - t0

    print(f"\n=== Top-{k} 判例（検索 {t_retrieve*1000:.0f}ms）===")
    for i, r in enumerate(rows, 1):
        cn = r.get("case_number", "")
        court = r.get("court_name", "")
        cname = r.get("case_name", "")
        src = r.get("text_source", "")
        dist = r.get("_distance", 0)
        print(f"  [{i}] dist={dist:.3f} src={src} | [{cn}] {court}")
        print(f"      {cname[:80]}")

    if retrieve_only:
        return

    ctx = format_context(rows)
    user_prompt = f"""【ユーザー質問】
{question}

【検索された判例】
{ctx}

上記判例を根拠に、ユーザーの質問に日本語で答えてください。"""

    print(f"\n=== {llm_model} の回答 ===")
    t1 = time.time()
    call_ollama(llm_model, SYSTEM_PROMPT, user_prompt, stream=True)
    print(f"\n[LLM 生成時間: {time.time()-t1:.1f}s]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="?", help="質問文")
    ap.add_argument("-k", "--k", type=int, default=DEFAULT_K)
    ap.add_argument("-m", "--model", default=DEFAULT_LLM)
    ap.add_argument("-i", "--interactive", action="store_true")
    ap.add_argument("--retrieve-only", action="store_true", help="LLMを呼ばず検索結果のみ表示")
    args = ap.parse_args()

    print(f"Loading embed model on {'cuda' if torch.cuda.is_available() else 'cpu'}...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    embed_model = SentenceTransformer(EMBED_MODEL, device=device)

    print(f"Connecting lancedb at {DB_PATH}...")
    db = lancedb.connect(str(DB_PATH))
    table = db.open_table(TABLE_NAME)
    print(f"Table rows: {table.count_rows():,}")

    if args.interactive:
        print("\n=== Interactive mode (Ctrl+C to exit) ===")
        while True:
            try:
                q = input("\n> 質問: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not q:
                continue
            run_query(table, embed_model, q, args.k, args.model, args.retrieve_only)
    else:
        if not args.question:
            ap.print_help()
            sys.exit(1)
        run_query(table, embed_model, args.question, args.k, args.model, args.retrieve_only)


if __name__ == "__main__":
    main()
