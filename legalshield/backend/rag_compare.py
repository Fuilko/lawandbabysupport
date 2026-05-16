"""
RAG モデル比較ツール — 同じ質問・同じ検索結果を 3 モデルに投入し、
回答品質と所要時間を並べた HTML レポートを生成。

Usage:
  python rag_compare.py "質問文" [--k 6] [--out compare_report.html]
"""
from __future__ import annotations

import argparse
import html as html_lib
import sys
import time
from datetime import datetime
from pathlib import Path

import lancedb
import torch
from sentence_transformers import SentenceTransformer

from rag_query import (
    DB_PATH, TABLE_NAME, EMBED_MODEL,
    SYSTEM_PROMPT, DEFAULT_K,
    embed_query, retrieve, format_context, call_ollama,
)

MODELS = ["phi4:14b", "gemma3:27b", "llama3.3:70b"]


def render_html(question: str, rows: list, results: list[dict], k: int) -> str:
    # context summary cards
    case_cards = []
    for i, r in enumerate(rows, 1):
        cn = html_lib.escape(str(r.get("case_number", "")))
        court = html_lib.escape(str(r.get("court_name", "")))
        cname = html_lib.escape(str(r.get("case_name", "")))
        dist = r.get("_distance", 0)
        src = html_lib.escape(str(r.get("text_source", "")))
        case_cards.append(
            f'<div class="case"><span class="cn">[{cn}]</span> '
            f'<span class="court">{court}</span> '
            f'<span class="dist">dist={dist:.3f} src={src}</span><br>'
            f'<span class="cname">{cname}</span></div>'
        )

    # model answer columns
    model_cols = []
    for res in results:
        ans_html = html_lib.escape(res["answer"]).replace("\n", "<br>")
        err = ""
        if res.get("error"):
            err = f'<div class="err">⚠ {html_lib.escape(res["error"])}</div>'
        model_cols.append(f"""
<div class="col">
  <h3>{html_lib.escape(res['model'])}</h3>
  <div class="meta">
    所要時間: <b>{res['elapsed']:.1f}s</b><br>
    回答長: {res['length']} 文字
  </div>
  {err}
  <div class="answer">{ans_html}</div>
</div>""")

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    q_html = html_lib.escape(question)

    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<title>RAG モデル比較 — {q_html[:30]}</title>
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, "Segoe UI", "Noto Sans JP", sans-serif;
       background: #0d1117; color: #c9d1d9; padding: 24px; line-height: 1.6;
       max-width: 1600px; margin: 0 auto; }}
h1 {{ color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 8px; }}
h2 {{ color: #79c0ff; margin-top: 32px; }}
h3 {{ color: #d2a8ff; }}
.meta {{ color: #8b949e; font-size: 0.85em; margin: 8px 0 16px; }}
.question {{ background: #161b22; padding: 16px; border-radius: 6px;
             border-left: 4px solid #d2a8ff; font-size: 1.05em; }}
.case {{ background: #161b22; padding: 10px 14px; border-radius: 4px;
        margin: 6px 0; border-left: 3px solid #58a6ff; font-size: 0.9em; }}
.cn {{ color: #58a6ff; font-weight: bold; }}
.court {{ color: #c9d1d9; }}
.dist {{ color: #8b949e; font-size: 0.8em; margin-left: 8px; }}
.cname {{ color: #8b949e; font-size: 0.85em; }}
.cols {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;
        margin-top: 16px; }}
.col {{ background: #161b22; padding: 18px; border-radius: 8px;
       border-left: 4px solid #3fb950; min-width: 0; }}
.answer {{ background: #0d1117; padding: 14px; border-radius: 6px;
          font-size: 0.92em; white-space: pre-wrap; word-wrap: break-word; }}
.err {{ color: #f85149; background: #2d1518; padding: 8px; border-radius: 4px;
      margin-bottom: 8px; }}
@media (max-width: 1200px) {{ .cols {{ grid-template-columns: 1fr; }} }}
</style></head><body>

<h1>⚖️ RAG モデル品質比較</h1>
<p class="meta">生成日時: {ts} ｜ Top-K: {k}</p>

<h2>質問</h2>
<div class="question">{q_html}</div>

<h2>検索された判例 (Top-{k})</h2>
{"".join(case_cards)}

<h2>各モデルの回答</h2>
<div class="cols">{"".join(model_cols)}</div>

</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("-k", "--k", type=int, default=DEFAULT_K)
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()

    print(f"Loading embed model on {'cuda' if torch.cuda.is_available() else 'cpu'}...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    embed_model = SentenceTransformer(EMBED_MODEL, device=device)

    print(f"Connecting LanceDB...")
    db = lancedb.connect(str(DB_PATH))
    table = db.open_table(TABLE_NAME)

    print(f"\n=== Question ===\n{args.question}\n")
    t0 = time.time()
    qvec = embed_query(embed_model, args.question)
    rows = retrieve(table, qvec, args.k)
    print(f"=== Retrieved Top-{args.k} in {(time.time()-t0)*1000:.0f}ms ===")
    for i, r in enumerate(rows, 1):
        print(f"  [{i}] [{r.get('case_number','')}] {r.get('court_name','')} | "
              f"{(r.get('case_name','') or '')[:60]}")

    ctx = format_context(rows)
    user_prompt = f"""【ユーザー質問】
{args.question}

【検索された判例】
{ctx}

上記判例を根拠に、ユーザーの質問に日本語で答えてください。"""

    results = []
    for model in MODELS:
        print(f"\n=== {model} ===")
        t1 = time.time()
        try:
            ans = call_ollama(model, SYSTEM_PROMPT, user_prompt, stream=True)
            elapsed = time.time() - t1
            results.append({
                "model": model,
                "answer": ans,
                "elapsed": elapsed,
                "length": len(ans),
                "error": None,
            })
            print(f"\n[{model}: {elapsed:.1f}s, {len(ans)} chars]")
        except Exception as e:
            elapsed = time.time() - t1
            print(f"\n⚠ {model} failed: {e}")
            results.append({
                "model": model,
                "answer": "",
                "elapsed": elapsed,
                "length": 0,
                "error": str(e),
            })

    out_path = args.out or f"compare_{datetime.now():%Y%m%d_%H%M%S}.html"
    out_file = Path(out_path)
    out_file.write_text(render_html(args.question, rows, results, args.k), encoding="utf-8")

    print(f"\n=== Summary ===")
    for r in results:
        status = "❌" if r["error"] else "✅"
        print(f"  {status} {r['model']:20s} {r['elapsed']:6.1f}s  {r['length']} chars")
    print(f"\n📄 HTML レポート: {out_file.resolve()}")


if __name__ == "__main__":
    main()
