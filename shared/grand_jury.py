#!/usr/bin/env python3
"""
grand_jury.py — 大陪審團模擬 (CrewAI)

5 個 Agent 對你的案件進行攻防模擬:
  1. 案情整理官 (Case Analyst)
  2. 原告律師 (Plaintiff Attorney)
  3. 被告律師 (Defense Attorney)
  4. 裁判官 (Judge)
  5. 書記官 (Court Clerk)

用法:
  python shared/grand_jury.py --case-file path/to/case.md
  python shared/grand_jury.py --case-file path/to/case.md --model ollama/llama3.2:3b
  python shared/grand_jury.py --case-file path/to/case.md --model openai/gpt-4o
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from crewai import Agent, Crew, Task, Process


# --- Agent 定義 ---

def create_case_analyst(model: str) -> Agent:
    return Agent(
        role="案情整理官",
        goal="証拠と事実関係を正確に整理し、法的争点を特定する",
        backstory=(
            "あなたは20年以上の経験を持つ法律パラリーガルです。"
            "膨大な証拠資料から重要な事実を抽出し、時系列で整理する能力に長けています。"
            "感情を排除し、客観的事実のみに基づいて案件を分析します。"
        ),
        verbose=True,
        allow_delegation=False,
        llm=model,
    )


def create_plaintiff_attorney(model: str) -> Agent:
    return Agent(
        role="原告側弁護士",
        goal="原告の利益を最大化する法的主張を構築する",
        backstory=(
            "あなたは製造物責任法（PL法）と消費者保護法の専門弁護士です。"
            "15年以上の訴訟経験があり、特に製品欠陥訴訟での勝率が高いことで知られています。"
            "原告の権利回復のため、最も効果的な法的戦略を立案します。"
            "必ず条文番号を引用してください。"
        ),
        verbose=True,
        allow_delegation=False,
        llm=model,
    )


def create_defense_attorney(model: str) -> Agent:
    return Agent(
        role="被告側弁護士",
        goal="被告の立場から原告の主張の弱点を見つけ、反論を構築する",
        backstory=(
            "あなたはメーカー側を代理する企業法務の専門弁護士です。"
            "製造物責任訴訟において被告側を多数代理してきました。"
            "原告の主張の論理的弱点、証拠の不備、因果関係の欠如を鋭く指摘します。"
            "容赦なく反論してください。これは原告側の準備を助けるためです。"
        ),
        verbose=True,
        allow_delegation=False,
        llm=model,
    )


def create_judge(model: str) -> Agent:
    return Agent(
        role="裁判官",
        goal="双方の主張を公平に評価し、勝訴可能性と改善点を指摘する",
        backstory=(
            "あなたは地方裁判所の民事部裁判官として20年の経験があります。"
            "製造物責任法関連の判例に精通しており、"
            "過去の判例との整合性を常に確認しながら判断します。"
            "原告・被告双方の主張を冷静に評価し、勝訴確率を%で示してください。"
        ),
        verbose=True,
        allow_delegation=False,
        llm=model,
    )


def create_clerk(model: str) -> Agent:
    return Agent(
        role="書記官",
        goal="全体の議論を整理し、実用的な法律文書の草案を作成する",
        backstory=(
            "あなたは裁判所書記官として、訴状・準備書面・判決文の作成に精通しています。"
            "議論の結果を踏まえ、実際に裁判所に提出可能な文書フォーマットで"
            "訴状の草案を作成します。日本の民事訴訟法の書式に従ってください。"
        ),
        verbose=True,
        allow_delegation=False,
        llm=model,
    )


# --- Task 定義 ---

def create_tasks(
    case_analyst: Agent,
    plaintiff: Agent,
    defense: Agent,
    judge: Agent,
    clerk: Agent,
    case_text: str,
) -> list[Task]:
    return [
        Task(
            description=(
                f"以下の案件資料を読み、事実関係を時系列で整理し、"
                f"法的争点を5つ以内に特定してください。\n\n"
                f"--- 案件資料 ---\n{case_text}\n--- 案件資料終 ---"
            ),
            expected_output=(
                "1. 事実関係の時系列整理\n"
                "2. 当事者関係図\n"
                "3. 法的争点リスト（最大5つ）\n"
                "4. 適用可能な法令リスト"
            ),
            agent=case_analyst,
        ),
        Task(
            description=(
                "案情整理官の分析結果を踏まえ、原告として最も効果的な法的主張を構築してください。\n\n"
                "以下を含めてください：\n"
                "1. 請求の趣旨（何をいくら請求するか）\n"
                "2. 請求原因（法的根拠 — 条文番号必須）\n"
                "3. 主要な証拠と立証計画\n"
                "4. 予想される反論への事前対策"
            ),
            expected_output=(
                "1. 請求の趣旨\n"
                "2. 請求原因（製造物責任法、民法、消費者契約法の条文引用）\n"
                "3. 証拠リストと立証計画\n"
                "4. 反論対策"
            ),
            agent=plaintiff,
        ),
        Task(
            description=(
                "原告側弁護士の主張を読み、被告（製造者）の立場から徹底的に反論してください。\n\n"
                "以下の観点から攻撃してください：\n"
                "1. 因果関係の否認（欠陥と損害の因果関係は立証されているか）\n"
                "2. 使用者の過失（原告側の操作ミスの可能性）\n"
                "3. 損害額の争い（請求額は妥当か）\n"
                "4. 消滅時効・除斥期間\n"
                "5. その他の抗弁"
            ),
            expected_output=(
                "1. 因果関係への反論\n"
                "2. 過失相殺の主張\n"
                "3. 損害額への反論\n"
                "4. 消滅時効等の手続的抗弁\n"
                "5. 総合評価：原告主張の弱点リスト"
            ),
            agent=defense,
        ),
        Task(
            description=(
                "原告・被告双方の主張を評価し、判決を下してください。\n\n"
                "以下を含めてください：\n"
                "1. 各争点についての判断（原告/被告どちらの主張が強いか）\n"
                "2. 過去の類似判例との比較\n"
                "3. 原告の勝訴確率（%）\n"
                "4. 原告が勝訴するために必要な追加証拠・改善点\n"
                "5. 和解の可能性と推奨和解金額"
            ),
            expected_output=(
                "1. 各争点の判断\n"
                "2. 判例比較\n"
                "3. 勝訴確率: ___%\n"
                "4. 改善すべき点リスト\n"
                "5. 和解推奨案"
            ),
            agent=judge,
        ),
        Task(
            description=(
                "以上の議論結果を踏まえ、裁判所に提出可能な訴状の草案を作成してください。\n\n"
                "日本の民事訴訟法の書式に従い：\n"
                "- 表題: 訴状\n"
                "- 当事者の表示\n"
                "- 請求の趣旨\n"
                "- 請求の原因（第1〜第N章）\n"
                "- 証拠方法\n"
                "- 附属書類"
            ),
            expected_output="完全な訴状草案（裁判所提出フォーマット）",
            agent=clerk,
        ),
    ]


def run_grand_jury(
    case_text: str,
    model: str = "ollama/llama3.2:3b",
    output_dir: Optional[Path] = None,
) -> str:
    """大陪審団シミュレーションを実行"""

    # Agent 作成
    analyst = create_case_analyst(model)
    plaintiff = create_plaintiff_attorney(model)
    defense = create_defense_attorney(model)
    judge = create_judge(model)
    clerk = create_clerk(model)

    # Task 作成
    tasks = create_tasks(analyst, plaintiff, defense, judge, clerk, case_text)

    # Crew 作成 + 実行
    crew = Crew(
        agents=[analyst, plaintiff, defense, judge, clerk],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    # 結果保存
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"grand_jury_{timestamp}.md"
        output_file.write_text(str(result), encoding="utf-8")
        print(f"\n→ 結果保存: {output_file}")

    return str(result)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="大陪審團模擬")
    parser.add_argument("--case-file", required=True, help="案件資料ファイル (Markdown/TXT)")
    parser.add_argument("--model", default="ollama/llama3.2:3b", help="LLM モデル")
    parser.add_argument("--output-dir", default="shared/output/jury", help="出力ディレクトリ")

    args = parser.parse_args()

    case_path = Path(args.case_file)
    if not case_path.exists():
        print(f"エラー: {case_path} が見つかりません")
        return

    case_text = case_path.read_text(encoding="utf-8")
    print(f"案件資料読み込み: {case_path} ({len(case_text)} 文字)")
    print(f"使用モデル: {args.model}")
    print(f"出力先: {args.output_dir}")
    print()

    run_grand_jury(
        case_text=case_text,
        model=args.model,
        output_dir=Path(args.output_dir),
    )


if __name__ == "__main__":
    main()
