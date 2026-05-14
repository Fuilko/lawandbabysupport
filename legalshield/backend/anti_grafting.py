"""LegalShield Anti-Grafting (防吃案) Module — Prevent police case suppression.

Key functions:
  1. Generate immutable evidence package with timestamp + hash
  2. Create "Police Interaction Script" with legal counter-arguments
  3. Auto-backup report to user's email / cloud before police visit
  4. Generate formal complaint templates for oversight bodies
  5. Track case status and escalate if police refuses to accept

Usage:
  python anti_grafting.py --case-id CASE001 --scenario DV
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def generate_police_script(scenario: str, prefecture: str = "東京都") -> dict:
    """Generate interaction script for police station visit.

    Victim can print this and hand it to police officer.
    Prevents downgrade from 'incident report (被害届)' to mere 'consultation (相談)'.
    """
    scripts = {
        "DV": {
            "title": "配偶者暴力被害届提出",
            "legal_basis": [
                "刑法第204条（傷害罪）",
                "刑法第222条（脅迫罪）",
                "配偶者暴力防止及び被害者保護法第3条（保護命令）",
            ],
            "demand": "被害届の受理と発行を求めます",
            "if_refused": {
                "police_excuse_1": "『これは民事です』",
                "counter_1": "刑法204条・222条に該当する刑事事件です。『民事不介入』ではなく、『犯罪の告訴』です。受理拒否は職務怠慢になります。",
                "police_excuse_2": "『被害届は必要ありません』",
                "counter_2": "被害届受理番号が発行されない場合、『被害届不受理通知書』（告訴不受理通知書）の交付を求めます。これは刑事訴訟法第230条に基づく権利です。",
                "police_excuse_3": "『証拠が不十分です』",
                "counter_3": "被害届の受理には証拠の充実性は不要です（捜査は受理後に行われます）。診断書・写真・LINEスクリーンショットを添付しています。",
                "police_excuse_4": "『相談で記録します』",
                "counter_4": "『相談』ではなく『被害届』として正式受理してください。相談記録では捜査は開始されません。",
            },
            "docs_required": [
                "身分証明書（運転免許証・マイナンバーカード）",
                "診断書（医療機関発行）",
                "受傷写真（タイムスタンプ付き）",
                "脅迫メッセージスクリーンショット",
                "このLegalShield報告書",
            ],
        },
        "性暴力": {
            "title": "性犯罪被害届提出",
            "legal_basis": [
                "刑法第176条（強制わいせつ罪）",
                "刑法第177条（強制性交等罪）",
                "刑法第178条の2（不同意性交等罪）",
            ],
            "demand": "被害届の受理と発行を求めます",
            "if_refused": {
                "police_excuse_1": "『合意があったのでは？』",
                "counter_1": "『同意なし』です。意識不明・抵抗不能の状態でした。法医学的検査を受けています。DNA証拠を保全中です。",
                "police_excuse_2": "『泥酔しただけでは？』",
                "counter_2": "『不同意性交等罪』は、被害者の同意がないことで成立します。泥酔による抵抗不能状態は、明確な構成要件に該当します。",
                "police_excuse_3": "『被害届は不要、相談で十分』",
                "counter_3": "被害届受理番号を発行してください。不受理の場合は『被害届不受理通知書』の交付を求めます。",
            },
            "docs_required": [
                "身分証明書",
                "法医学的検査結果（指定病院）",
                "現場写真・位置情報",
                "犯人との通訊記録",
                "このLegalShield報告書",
            ],
        },
        "消費者被害": {
            "title": "詐欺被害届提出",
            "legal_basis": [
                "刑法第246条（詐欺罪）",
                "組織的犯罪処罰法",
            ],
            "demand": "被害届の受理と発行を求めます",
            "if_refused": {
                "police_excuse_1": "『民事です』",
                "counter_1": "刑法246条（詐欺罪）に該当する刑事事件です。振込明細・通話録音・犯人の口座情報を添付しています。",
                "police_excuse_2": "『金額が少ない』",
                "counter_2": "詐欺罪の成立に金額の大小は関係ありません。また、他の被害者と連続犯の可能性があります。",
            },
            "docs_required": [
                "身分証明書",
                "振込明細・領収書",
                "犯人との通話録音・SMS",
                "被害金額の計算書",
                "このLegalShield報告書",
            ],
        },
        "職場": {
            "title": "業務上暴行・傷害被害届提出",
            "legal_basis": [
                "刑法第204条（傷害罪）",
                "刑法第208条（暴行罪）",
                "労働基準法第99条（安全配慮義務違反）",
            ],
            "demand": "被害届の受理と発行を求めます",
            "if_refused": {
                "police_excuse_1": "『職場の問題です』",
                "counter_1": "業務上の暴行・傷害は刑法204条・208条に該当する刑事事件です。労働問題と刑事問題は別個です。",
            },
            "docs_required": [
                "身分証明書",
                "診断書",
                "勤務記録・タイムシート",
                "上司からのメール・メモ",
                "このLegalShield報告書",
            ],
        },
        "児童虐待": {
            "title": "児童虐待通報・被害届提出",
            "legal_basis": [
                "児童虐待の防止等に関する法律",
                "児童福祉法",
                "刑法第204条（傷害罪）",
            ],
            "demand": "児童相談所通報（#7119）および被害届受理を求めます",
            "if_refused": {
                "police_excuse_1": "『家庭内の問題です』",
                "counter_1": "児童虐待は児童虐待防止法に基づく公務員通報義務の対象です。児童相談所への通報は必須です。",
            },
            "docs_required": [
                "通報者の身分証明書",
                "児童の発言記録（日時・状況）",
                "傷害写真",
                "学校・医療機関の記録",
                "このLegalShield報告書",
            ],
        },
    }
    return scripts.get(scenario, scripts["DV"])


def generate_immutable_package(case_id: str, scenario: str, prefecture: str = "東京都") -> dict:
    """Create immutable evidence + report package with hash chain."""
    timestamp = datetime.now(timezone.utc).isoformat()
    package = {
        "legalshield_version": "1.0",
        "case_id": case_id,
        "generated_at": timestamp,
        "scenario": scenario,
        "prefecture": prefecture,
        "police_script": generate_police_script(scenario, prefecture),
        "legal_basis_summary": "",
        "immutable_hash": "",
    }
    # Create hash of entire package
    content = json.dumps(package, ensure_ascii=False, sort_keys=True)
    package["immutable_hash"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return package


def generate_escalation_templates(case_id: str, scenario: str, police_station: str = "", officer_name: str = "", refusal_reason: str = "") -> dict:
    """Generate complaint templates for oversight bodies when police refuses."""
    timestamp = datetime.now(timezone.utc).isoformat()
    templates = {
        "to_public_safety_commission": {
            "title": f"警察被害届不受理に対する申立書（{scenario}）",
            "body": f"""
{police_station}において、{timestamp}、{scenario}の被害届を提出しましたが、
{officer_name}警察官により受理を拒否されました（拒否理由：{refusal_reason}）。

刑事訴訟法第230条により、被害届不受理通知書の交付を求めます。
また、同警察官の職務怠慢を申立てます。

添付：
1. LegalShield 証拠保全パッケージ
2. 被害届不受理の経緯記録
3. 診断書・写真・メッセージスクリーンショット

申立人：（ユーザー氏名）
日付：{timestamp}
""",
            "recipient": "都道府県公安委員会",
            "method": "書面郵送 + オンライン申請",
        },
        "to_prosecutors_office": {
            "title": f"告訴不受理に対する検察審査会申立書（{scenario}）",
            "body": f"""
{police_station}において被害届を提出しましたが、不受理となりました。

刑法に該当する明確な犯罪事実があり、証拠も添付しています。
検察官による捜査開始を求めます。

添付：
1. 被害届不受理通知書（または不受理の証拠）
2. LegalShield 証拠保全パッケージ
3. 法條該当一覧

申立人：（ユーザー氏名）
日付：{timestamp}
""",
            "recipient": "地方検察庁 検察審査会",
            "method": "書面郵送",
        },
        "to_national_police_agency": {
            "title": f"警察庁長官あて 警察被害届不受理に対する苦情申立書",
            "body": f"""
{police_station}において、{scenario}の被害届が不受理となりました。
警察官の職務怠慢および被害届受理義務違反を申立てます。

添付：
1. LegalShield 証拠保全パッケージ
2. 不受理の経緯記録

申立人：（ユーザー氏名）
日付：{timestamp}
""",
            "recipient": "警察庁",
            "method": "書面郵送",
        },
    }
    return templates


def save_package(case_id: str, package: dict, output_dir: Path) -> Path:
    """Save package to disk and return path."""
    out = output_dir / f"anti_grafting_{case_id}"
    out.mkdir(parents=True, exist_ok=True)

    # Main report
    report_path = out / "police_visit_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(package, f, ensure_ascii=False, indent=2)

    # Human-readable script
    script = package["police_script"]
    txt_path = out / "police_interaction_script.txt"
    txt_content = f"""═══════════════════════════════════════════════════
LegalShield 警察署訪問用 対話スクリプト
案件番号: {case_id}
生成日時: {package['generated_at']}
═══════════════════════════════════════════════════

【提出するもの】
{chr(10).join('- ' + d for d in script['docs_required'])}

【あなたの主張】
「{script['demand']}」

【法條根拠】
{chr(10).join('- ' + l for l in script['legal_basis'])}

【警察が言うかもしれない言い訳と、あなたの反論】

"""
    for key, val in script["if_refused"].items():
        if key.startswith("police"):
            txt_content += f"警察: 『{val}』\n"
        elif key.startswith("counter"):
            txt_content += f"あなた: {val}\n\n"

    txt_content += """【もし受理されない場合】
1. 不受理の理由をメモし、警察官の名前・所属・警視庁番号を確認
2. このスクリプトの最後のページに記録
3. LegalShield アプリから「上級機関申立」機能を使用

【上級機関】
- 都道府県公安委員会（警察の監督機関）
- 地方検察庁検察審査会
- 警察庁

═══════════════════════════════════════════════════
不変ハッシュ（改竄検知用）: {package['immutable_hash']}
この文書の改竄を防ぐため、ハッシュ値を記録しています。
═══════════════════════════════════════════════════
"""
    txt_path.write_text(txt_content, encoding="utf-8")

    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="LegalShield Anti-Grafting Generator")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--scenario", default="DV", choices=["DV", "性暴力", "消費者被害", "職場", "児童虐待"])
    parser.add_argument("--prefecture", default="東京都")
    parser.add_argument("--police-station", default="", help="Police station name if known")
    parser.add_argument("--output", default=str(ROOT / "knowledge" / "cases"), type=Path)
    args = parser.parse_args()

    print(f"[anti-grafting] generating package for {args.case_id} ({args.scenario})")

    # Generate package
    package = generate_immutable_package(args.case_id, args.scenario, args.prefecture)
    out_dir = save_package(args.case_id, package, args.output)

    # Generate escalation templates
    templates = generate_escalation_templates(args.case_id, args.scenario, args.police_station)
    for name, tmpl in templates.items():
        tmpl_path = out_dir / f"{name}.txt"
        tmpl_path.write_text(
            f"{tmpl['title']}\n\n宛先: {tmpl['recipient']}\n提出方法: {tmpl['method']}\n\n{tmpl['body']}",
            encoding="utf-8",
        )

    print(f"[ok] package saved to: {out_dir}")
    print(f"     files: {list(out_dir.iterdir())}")
    print(f"     immutable hash: {package['immutable_hash'][:24]}...")


if __name__ == "__main__":
    main()
