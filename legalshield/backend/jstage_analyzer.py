"""J-STAGE Legal Paper Analyzer — Extract insights from academic legal papers.

Usage:
    python jstage_analyzer.py --input knowledge/seeds/jstage_legal_papers.json
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def load_papers(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_year(date_str: str) -> int:
    """Extract 4-digit year from date string."""
    m = re.search(r"(20\d{2})", date_str)
    if m:
        return int(m.group(1))
    return 0


def analyze_papers(papers: list[dict]) -> dict:
    """Analyze corpus of legal papers and return insights."""
    df = pd.DataFrame(papers)
    insights = {}

    # 1. Volume by year
    df["year_num"] = df["year"].apply(extract_year)
    year_counts = df[df["year_num"] > 0]["year_num"].value_counts().sort_index()
    insights["trend_by_year"] = year_counts.to_dict()

    # 2. Top journals
    insights["top_journals"] = df["journal"].value_counts().head(10).to_dict()

    # 3. Keyword frequency
    all_keywords = []
    for kw_list in df.get("keywords", pd.Series([])):
        if isinstance(kw_list, list):
            all_keywords.extend(kw_list)
    insights["top_keywords"] = Counter(all_keywords).most_common(30)

    # 4. Crime type classification from titles
    crime_patterns = {
        "DV_配偶者暴力": ["配偶者暴力", "DV", "domestic violence", "虐待", "児童虐待"],
        "性犯罪": ["性犯罪", "性暴力", "強制性交", "わいせつ", "不同意", "レイプ", "sexual assault"],
        "消費者_詐欺": ["詐欺", "消費者被害", "特殊詐欺", "振り込め", "架空請求"],
        "職場": ["パワーハラスメント", "職場", "セクハラ", "労働"],
        "ストーカー": ["ストーカー", "stalker", "つきまとい"],
        "サイバー犯罪": ["サイバー", "ネット", "いじめ", "cyber"],
        "薬物": ["薬物", "覚せい剤", "依存", "drug"],
        "ヘイトクライム": ["ヘイト", "差別", "hate crime"],
        "一般被害者": ["被害者", "victimology", "支援", "rights"],
    }

    crime_counts = {k: 0 for k in crime_patterns}
    for title in df["title"]:
        t = str(title).lower()
        for crime, patterns in crime_patterns.items():
            for p in patterns:
                if p.lower() in t:
                    crime_counts[crime] += 1
                    break
    insights["crime_type_distribution"] = crime_counts

    # 5. Abstract sentiment/topics (simple keyword)
    support_keywords = ["支援", "支援", "保護", "権利", "相談", "intervention", "support"]
    victim_keywords = ["被害者", "被害", "trauma", "二次被害"]
    legal_keywords = ["判例", "法廷", "量刑", "判決", "precedent", "court"]

    support_count = sum(1 for a in df.get("abstract", pd.Series([])) if any(k in str(a) for k in support_keywords))
    victim_count = sum(1 for a in df.get("abstract", pd.Series([])) if any(k in str(a) for k in victim_keywords))
    legal_count = sum(1 for a in df.get("abstract", pd.Series([])) if any(k in str(a) for k in legal_keywords))

    insights["abstract_themes"] = {
        "support_focused": support_count,
        "victim_focused": victim_count,
        "legal_precedent_focused": legal_count,
    }

    # 6. Paper metadata stats
    insights["total_papers"] = len(df)
    insights["with_abstract"] = int(df["abstract"].notna().sum())
    insights["with_pdf"] = int(df["pdf_link"].notna().sum())

    return insights


def generate_markdown_report(insights: dict, output_path: Path) -> None:
    """Generate human-readable analysis report."""
    lines = [
        "# J-STAGE 法律論文・判例分析レポート\n",
        f"**分析日**: {pd.Timestamp.now().strftime('%Y-%m-%d')}  ",
        f"**対象論文数**: {insights['total_papers']} 件",
        f"**アブストラクト付き**: {insights['with_abstract']} 件",
        f"**PDFリンク付き**: {insights['with_pdf']} 件\n",
        "---\n",
        "## 1. 犯罪タイプ別論文分布\n",
    ]

    sorted_crimes = sorted(insights["crime_type_distribution"].items(), key=lambda x: x[1], reverse=True)
    for crime, count in sorted_crimes:
        if count > 0:
            bar = "█" * min(count, 30)
            lines.append(f"- **{crime}**: {count} 件 {bar}\n")

    lines.extend([
        "\n## 2. トレンド（年次別論文数）\n",
    ])
    for year, count in insights["trend_by_year"].items():
        lines.append(f"- {year}: {count} 件\n")

    lines.extend([
        "\n## 3. 主要キーワード\n",
    ])
    for kw, count in insights["top_keywords"][:20]:
        lines.append(f"- **{kw}**: {count} 回\n")

    lines.extend([
        "\n## 4. アブストラクトテーマ分析\n",
    ])
    for theme, count in insights["abstract_themes"].items():
        lines.append(f"- {theme}: {count} 件\n")

    lines.extend([
        "\n## 5. 主要掲載誌\n",
    ])
    for journal, count in insights["top_journals"].items():
        lines.append(f"- {journal}: {count} 件\n")

    lines.extend([
        "\n---\n",
        "## 考察・LegalShield への示唆\n",
        "\n### 研究トレンドから見る課題\n",
        "1. **研究が集中している領域**が、実際の被害発生率と一致しているか確認する必要がある。",
        "   例: 学術論文が少ない『消費者被害』『サイバー犯罪』が、実社会では急増している可能性。",
        "\n2. **被害者支援に焦点を当てた論文**が全体の何%を占めるかが、社会的関心の度合いを示す。",
        "   多くの論文が『犯罪者の量刑』に焦点を当て、『被害者の回復』に焦点を当てていない場合、",
        "   政策・実務のバランスが偏っている可能性がある。",
        "\n3. **判例分析論文**の有無と内容から、司法の傾向を把握できる。",
        "   例: 不同意性交等罪の判例分析が増加 → 2023年刑法改正の影響が研究に反映されている。",
        "\n### LegalShield への活用方針\n",
        "- 頻出キーワードを LegalShield の AI トレーニング辞書に追加\n",
        "- 判例分析論文から『傾向と対策』を RAG 検索の優先コンテンツに指定\n",
        "- 論文数が少ない犯罪タイプ（例: サイバー犯罪）を優先的に拡充\n",
        "- 被害者支援に焦点を当てた論文の知見を、AI の対話スクリプトに反映\n",
    ])

    output_path.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="J-STAGE Legal Paper Analyzer")
    parser.add_argument("--input", default=str(ROOT / "knowledge" / "seeds" / "jstage_legal_papers.json"), type=Path)
    parser.add_argument("--output", default=str(ROOT / "knowledge" / "seeds" / "jstage_analysis_report.md"), type=Path)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"[error] Input not found: {args.input}")
        print("Run: python crawlers/jstage_search.py --batch --max 15")
        return

    papers = load_papers(args.input)
    insights = analyze_papers(papers)
    generate_markdown_report(insights, args.output)

    print(f"[ok] Analyzed {insights['total_papers']} papers")
    print(f"[ok] Report saved to {args.output}")

    # Print summary
    print("\n--- Quick Summary ---")
    print(f"Total papers: {insights['total_papers']}")
    print(f"With abstract: {insights['with_abstract']}")
    print(f"Top crime types:")
    for crime, count in sorted(insights["crime_type_distribution"].items(), key=lambda x: x[1], reverse=True)[:5]:
        if count > 0:
            print(f"  {crime}: {count}")


if __name__ == "__main__":
    main()
