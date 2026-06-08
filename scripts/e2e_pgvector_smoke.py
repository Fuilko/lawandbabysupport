"""E2E smoke test: pgvector + harness L1-L7

uvicorn を起動せず、in-process で /rag/answer 相当を実行する（Ollama も任意）。

使い方:
    # pgvector 起動 + ETL 完了 + (任意) ollama 起動 後:
    python scripts/e2e_pgvector_smoke.py

    # Ollama 無しでも retrieval だけ確認可:
    python scripts/e2e_pgvector_smoke.py --no-llm

何を確認するか:
  1. pgvector に十分な行数があるか（precedents > 0）
  2. embed → cosine 検索が動くか（Source が返るか）
  3. harness L1 (intent) / L2 (retrieval gate) が両方動くか
  4. Ollama 有り時: L4 generation + L5 verify + L6 transparency までの output 形を確認
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# repo root を import 可能にする
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# pgvector を強制
os.environ.setdefault("LEGALSHIELD_RETRIEVE_BACKEND", "pg")

from legalshield.backend import harness, pgvector_retrieve as pgr  # noqa: E402


def make_embed():
    from sentence_transformers import SentenceTransformer
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer("intfloat/multilingual-e5-small", device=device)

    def embed(text: str) -> list[float]:
        v = model.encode([f"query: {text}"], normalize_embeddings=True)[0]
        return v.tolist()
    return embed


def make_ollama_chat(model_name: str = "gemma3:27b"):
    import requests
    url = os.environ.get("LEGALSHIELD_OLLAMA_URL", "http://127.0.0.1:11434")

    def chat(system: str, user: str, temperature: float) -> str:
        r = requests.post(
            f"{url}/api/chat",
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "options": {"temperature": temperature, "num_ctx": 8192},
            },
            timeout=180,
        )
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "") or ""
    return chat


QUESTIONS = [
    "パワハラで退職を強要された場合の対処法を教えてください。",
    "オンライン詐欺で 30 万円を騙し取られました。被害届とは別に何ができますか？",
    "DV を受けています。緊急で身を守る方法を知りたい。",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true", help="Ollama を呼ばず retrieval のみ確認")
    ap.add_argument("--question", default=None)
    ap.add_argument("--top-k", type=int, default=6)
    ap.add_argument("--model", default="gemma3:27b")
    args = ap.parse_args()

    print("[1/4] pgvector health check ...")
    h = pgr.health_check()
    print("      ", json.dumps(h, ensure_ascii=False))
    if not h.get("ok"):
        print("      pgvector unhealthy — abort"); sys.exit(2)
    if h.get("precedents", 0) == 0:
        print("      precedents=0 — ETL 未完了の可能性。abort"); sys.exit(2)

    print("[2/4] embed model load ...")
    embed = make_embed()

    questions = [args.question] if args.question else QUESTIONS

    for i, q in enumerate(questions, 1):
        print(f"\n=== Q{i}: {q} ===")
        # L1
        intent = harness.classify_intent(q)
        print(f"L1 intent: {intent.to_public()}")

        # L2
        prec_fn = pgr.make_precedent_retriever(embed)
        stat_fn = pgr.make_statute_retriever(embed)
        t0 = time.time()
        sources, warnings = harness.retrieval_gate(
            q, retrieve_precedents=prec_fn, retrieve_statutes=stat_fn, top_k=args.top_k,
        )
        print(f"L2 retrieval: {len(sources)} sources in {(time.time()-t0)*1000:.0f}ms")
        for s in sources[:3]:
            print(f"   - [{s.id}] {s.kind} {s.citation} dist={s.score:.4f}")
        if warnings:
            print(f"   warnings: {warnings}")

        if args.no_llm:
            continue

        # L4-L7
        print("[3/4] L4 generation (Ollama) ...")
        try:
            llm = make_ollama_chat(args.model)
            t0 = time.time()
            result = harness.run_harness(
                q,
                retrieve_precedents=prec_fn,
                retrieve_statutes=stat_fn,
                llm_chat=llm,
                top_k=args.top_k,
                audit_path=ROOT / "lancedb" / "harness_audit_e2e.jsonl",
            )
            print(f"   elapsed: {(time.time()-t0):.1f}s, confidence={result['confidence']}, "
                  f"refused={result['refused']}, lawyer_required={result['lawyer_required']}")
            print(f"   answer (first 400 chars):\n{'-'*60}\n{result['answer'][:400]}\n{'-'*60}")
            print(f"   ungrounded_claims: {result['verification']['ungrounded_claims']}")
        except Exception as e:
            print(f"   Ollama 呼出失敗 (無視可): {e}")

    print("\n[4/4] DONE")


if __name__ == "__main__":
    main()
