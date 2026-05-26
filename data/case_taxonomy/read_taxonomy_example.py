"""
LegalShield Case Taxonomy — 外部 agent からの読込サンプル

iOS App と全く同じ taxonomy_v1.json を読んで、
- カテゴリ別パートナー機関リストを出力
- フェーズごとの案件分類を整列
- RAG 検索シードを取得

Usage:
    python data/case_taxonomy/read_taxonomy_example.py
"""

from __future__ import annotations

import json
from pathlib import Path

TAXONOMY_PATH = Path(__file__).parent / "taxonomy_v1.json"


def load() -> dict:
    return json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))


def print_summary() -> None:
    tx = load()
    print(f"version          : {tx['version']}")
    print(f"generated_at     : {tx['generated_at']}")
    print(f"categories total : {len(tx['categories'])}")
    print(f"urgency levels   : {[u['id'] for u in tx['urgency_levels']]}")
    print()


def list_categories_by_phase() -> None:
    tx = load()
    for phase in range(0, 6):
        items = [c for c in tx["categories"] if c["phase"] == phase]
        if not items:
            continue
        print(f"--- Phase {phase} ({len(items)} categories) ---")
        for c in items:
            print(f"  {c['id']:30s} | {c['label_jp']:18s} | urgency={c['default_urgency']}")
        print()


def get_partners(category_id: str) -> list[str]:
    """カテゴリ ID からデフォルト連携機関を返す（外部 agent はこれを Tier 2 dispatch ロジックに使える）"""
    tx = load()
    for c in tx["categories"]:
        if c["id"] == category_id:
            return c.get("default_partners", [])
    return []


def get_rag_seeds(category_id: str) -> list[str]:
    tx = load()
    for c in tx["categories"]:
        if c["id"] == category_id:
            return c.get("rag_query_seeds", [])
    return []


if __name__ == "__main__":
    print_summary()
    list_categories_by_phase()
    print("[partners] child_abuse →", get_partners("child_abuse"))
    print("[rag seeds] child_abuse →", get_rag_seeds("child_abuse"))
