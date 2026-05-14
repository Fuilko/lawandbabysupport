#!/usr/bin/env python3
"""
precedent_search.py — 判例搜尋工具

從 vendor/data_set/precedent/ 搜尋相關判例，
產出 Markdown 摘要 + JSON 格式的訓練資料。

用法:
  python shared/precedent_search.py "製造物責任" --limit 20
  python shared/precedent_search.py "契約不適合" --limit 10 --after 2015
  python shared/precedent_search.py "ドローン" --export-md
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Optional


PRECEDENT_DIR = Path(__file__).parent.parent / "vendor" / "data_set" / "precedent"


def era_to_year(era: str, year: int) -> int:
    """和暦 → 西暦"""
    base = {"Meiji": 1868, "Taisho": 1912, "Showa": 1926, "Heisei": 1989, "Reiwa": 2019}
    return base.get(era, 2000) + year - 1


def load_precedent(path: Path) -> Optional[dict]:
    """JSON 判例ファイルを読み込み"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        d = data.get("date", {})
        western_year = era_to_year(d.get("era", "Heisei"), d.get("year", 1))
        data["_western_year"] = western_year
        data["_western_date"] = f"{western_year}-{d.get('month', 1):02d}-{d.get('day', 1):02d}"
        data["_path"] = str(path)
        return data
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def search_precedents(
    keyword: str,
    *,
    limit: int = 50,
    after_year: int = 0,
    precedent_dir: Path = PRECEDENT_DIR,
) -> list[dict]:
    """キーワードで判例を検索"""
    results: list[dict] = []

    for json_file in sorted(precedent_dir.rglob("*.json")):
        try:
            text = json_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if keyword not in text:
            continue

        data = load_precedent(json_file)
        if data is None:
            continue

        if after_year > 0 and data["_western_year"] < after_year:
            continue

        results.append(data)
        if len(results) >= limit:
            break

    # 新しい順にソート
    results.sort(key=lambda x: x.get("_western_date", ""), reverse=True)
    return results


def format_markdown(results: list[dict], keyword: str) -> str:
    """判例一覧を Markdown で出力"""
    lines = [
        f"# 判例検索結果：「{keyword}」",
        f"",
        f"> 件数: {len(results)}件",
        f"> 検索日: {date.today().isoformat()}",
        f"",
        f"---",
        f"",
    ]

    for i, r in enumerate(results, 1):
        case_name = r.get("case_name", "不明")
        court = r.get("court_name", "不明")
        case_num = r.get("case_number", "不明")
        w_date = r.get("_western_date", "不明")
        link = r.get("detail_page_link", "")
        pdf_link = r.get("full_pdf_link", "")
        contents = r.get("contents", "")

        # 判決主文の冒頭 500 文字
        summary = contents[:500].replace("\n", " ") if contents else "（本文なし）"

        lines.append(f"## {i}. {case_name}")
        lines.append(f"")
        lines.append(f"| 項目 | 内容 |")
        lines.append(f"|------|------|")
        lines.append(f"| **裁判所** | {court} |")
        lines.append(f"| **事件番号** | {case_num} |")
        lines.append(f"| **判決日** | {w_date} |")
        if link:
            lines.append(f"| **詳細** | [{link}]({link}) |")
        if pdf_link:
            lines.append(f"| **PDF** | [{pdf_link}]({pdf_link}) |")
        lines.append(f"")
        lines.append(f"**主文/要旨 (冒頭500字):**")
        lines.append(f"")
        lines.append(f"> {summary}")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

    return "\n".join(lines)


def format_training_jsonl(results: list[dict], keyword: str) -> str:
    """訓練用 JSONL 形式で出力"""
    lines: list[str] = []
    for r in results:
        contents = r.get("contents", "")
        if not contents:
            continue

        entry = {
            "instruction": f"以下の判例について、事件の概要、争点、判決結果を要約してください。",
            "input": f"事件名: {r.get('case_name', '')}\n"
                     f"裁判所: {r.get('court_name', '')}\n"
                     f"事件番号: {r.get('case_number', '')}\n"
                     f"判決日: {r.get('_western_date', '')}\n"
                     f"キーワード: {keyword}\n"
                     f"判決文冒頭:\n{contents[:2000]}",
            "output": "",  # AI teacher で後から埋める
            "metadata": {
                "case_number": r.get("case_number", ""),
                "court": r.get("court_name", ""),
                "date": r.get("_western_date", ""),
                "link": r.get("detail_page_link", ""),
                "keyword": keyword,
            },
        }
        lines.append(json.dumps(entry, ensure_ascii=False))

    return "\n".join(lines)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="判例検索ツール")
    parser.add_argument("keyword", help="検索キーワード")
    parser.add_argument("--limit", type=int, default=50, help="最大件数")
    parser.add_argument("--after", type=int, default=0, help="西暦年以降")
    parser.add_argument("--export-md", action="store_true", help="Markdown ファイル出力")
    parser.add_argument("--export-jsonl", action="store_true", help="訓練用 JSONL 出力")
    parser.add_argument("--output-dir", type=str, default=".", help="出力先ディレクトリ")

    args = parser.parse_args()

    print(f"検索中: 「{args.keyword}」(limit={args.limit}, after={args.after})...")
    results = search_precedents(args.keyword, limit=args.limit, after_year=args.after)
    print(f"→ {len(results)} 件見つかりました。")

    if not results:
        print("判例が見つかりませんでした。")
        return

    # 常に概要を表示
    for i, r in enumerate(results[:10], 1):
        print(f"  {i}. [{r.get('_western_date', '?')}] {r.get('case_name', '?')} ({r.get('court_name', '?')})")
    if len(results) > 10:
        print(f"  ... 他 {len(results) - 10} 件")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_keyword = re.sub(r"[^\w]", "_", args.keyword)

    if args.export_md:
        md = format_markdown(results, args.keyword)
        md_path = output_dir / f"precedent_{safe_keyword}.md"
        md_path.write_text(md, encoding="utf-8")
        print(f"→ Markdown: {md_path}")

    if args.export_jsonl:
        jsonl = format_training_jsonl(results, args.keyword)
        jsonl_path = output_dir / f"precedent_{safe_keyword}.jsonl"
        jsonl_path.write_text(jsonl, encoding="utf-8")
        print(f"→ JSONL (訓練用): {jsonl_path}")


if __name__ == "__main__":
    main()
