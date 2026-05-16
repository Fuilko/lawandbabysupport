"""LegalShield Perpetrator Profiler — Analyze perpetrator type, tactics, and counter-arguments.

Usage:
    python perpetrator_profiler.py --scenario stalker --excuses "心配だから連絡してる"
    python perpetrator_profiler.py --scenario DV --excuses "お前が悪い 愛してるから"
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Perpetrator profile database
PERPETRATOR_DB = {
    "DV": {
        "label_ja": "配偶者暴力",
        "label_en": "Domestic Violence",
        "psych_profile": {
            "core_traits": ["支配欲", "所有欲", "ナルシシズム", "拒否不耐性"],
            "attachment_style": "執着型愛着または回避型愛着",
            "common_disorders": ["境界性パーソナリティ障害", "酔依存", "抑うつ"],
            "trigger_factors": ["飲酒", "薬物", "配偶者の自立行動", "拒否・別れ話"],
        },
        "behavior_patterns": [
            "段階的エスカレーション（言葉→物→身体）",
            "サイクル（緊張蓄積→爆発→蜜月期）",
            "被害者の社会的孤立を図る",
            "謝罪と再犯の繰り返し",
        ],
        "tactics": {
            "gaslighting": "被害者の記憶・感覚を否定し、自分は正しいと主張",
            "economic_abuse": "金銭を支配し、被害者を経済的に依存させる",
            "isolation": "友人・家族との接触を遮断",
            "intimidation": "物を壊す・ペットを脅す・自殺をちらつかせる",
        },
        "common_excuses": {
            "お前が悪いから": "被害者責任転嫁。DVは加害者の選択であり、被害者の行動に関係なく発生する。",
            "愛してるから": "愛を装った支配。愛は相手の意思を尊重することであり、暴力は支配である。",
            "酔っていた": "酔いは抑制を下げるだけ。根本的な支配欲・怒りがある。",
            "最後だと思った": "暴力の正当化。『最後』は何度も繰り返される。",
            "子供のため": "子供のためなら、まず安全な環境を提供することが先決。",
        },
        "counter_arguments": [
            "暴力は、たとえ1回でも許されません。",
            "愛する人を傷つける行為は、愛ではありません。",
            "酔いは『本音』を出すだけです。根本的な問題があります。",
            "『最後』という言葉は、すでに何度も聞いています。",
            "子供のためには、安全な家庭環境が何よりです。",
        ],
        "risk_indicators": [
            "別れ話をした後にエスカレーション",
            "武器の存在・購入",
            "ストーカー行為の併発",
            "『一緒に死のう』という発言",
            "被害者の就職・交友を妨害",
        ],
        "legal_articles": ["刑法204条（傷害）", "刑法222条（脅迫）", "配偶者暴力防止法"],
    },
    "性暴力": {
        "label_ja": "性暴力",
        "label_en": "Sexual Violence",
        "psych_profile": {
            "core_traits": ["支配欲", "共感能力の欠如", "ナルシシズム", "権力志向"],
            "attachment_style": "回避型または混乱型",
            "common_disorders": ["性嗜好障害", "反社会性パーソナリティ障害", "薬物依存"],
            "trigger_factors": ["権力の機会", "被害者の無力な状況", "飲酒・薬物", "過去の性暴力体験"],
        },
        "behavior_patterns": [
            "被害者選定（無力な人・信頼関係にある人）",
            "状況操作（飲酒・薬物・閉鎖的空間）",
            "事後の否認・矮小化・脅迫",
            "複数被害者の存在（連続犯の傾向）",
        ],
        "tactics": {
            "denial": "何も起きていない、同意があった",
            "minimization": "大げさに取り上げる、ただの軽いこと",
            "blame": "被害者の服装・行動が原因",
            "intimidation": "暴露で脅す・社会的地位で圧力",
        },
        "common_excuses": {
            "合意があった": "抵抗不能・意識不明状態では同意は成立しない。",
            "泥酔していた": "泥酔した被害者を利用することは、刑法178条の2に該当。",
            "大げさに取り上げている": "被害者の主観的恐怖は客観的被害の証拠となる。",
            "証拠がない": "法医学的証拠・証人・状況証拠で十分に立証可能。",
            "私の人生が台無しになる": "被害者の人生はすでに大きな被害を受けている。",
        },
        "counter_arguments": [
            "同意は、明確で自由な意思表示である必要があります。",
            "泥酔・睡眠・薬物状態での行為は、法律上同意がないものとみなされます。",
            "被害者の苦痛の大きさは、被害者が決めることです。",
            "性暴力は、痕跡が残る犯罪です。科学捜査で立証されます。",
            "加害者の人生より、被害者の人生が優先されます。",
        ],
        "risk_indicators": [
            "複数の被害者からの告発",
            "職権・社会的地位の濫用",
            "被害者への執拗な接触・脅迫",
            "児童・若者への接近",
        ],
        "legal_articles": ["刑法176条", "刑法177条", "刑法178条の2"],
    },
    "stalker": {
        "label_ja": "ストーカー",
        "label_en": "Stalking",
        "psych_profile": {
            "core_traits": ["執着", "拒否不耐性", "ナルシシズム", "現実検討能力の低下"],
            "attachment_style": "執着型愛着障害",
            "common_disorders": ["妄想性障害", "パーソナリティ障害", "うつ病"],
            "trigger_factors": ["別れ", "拒否", "被害者の新しい関係", "社会的挫折"],
        },
        "behavior_patterns": [
            "自宅・職場周辺の徘徊",
            "SNS・メール・電話の執拗な連絡",
            "第三者（家族・友人・職場）への接触",
            "プレゼント・郵便物の送付",
        ],
        "tactics": {
            "love_bombing": "過度な愛情表現で引き留める",
            "surveillance": "GPS・SNS監視・尾行",
            "isolation": "被害者の人間関係を破壊",
            "threat": "自殺・危害・暴露で脅す",
        },
        "common_excuses": {
            "心配だから": "心配を理由にした執着行為はストーカー行為です。",
            "愛してるから": "愛とは相手の自由を尊重することです。追うことは支配です。",
            "ただの偶然": "何度も『偶然』が続くことはありません。",
            "別れたのはお前が悪い": "別れの理由は別問題。追う権利はありません。",
            "お前が私をこうさせた": "自分の行為の責任を被害者に押し付けるのは加害者の典型です。",
        },
        "counter_arguments": [
            "心配を理由にした追跡は、法律上『ストーカー行為』です。",
            "愛するなら、相手の意思を尊重してください。",
            "『偶然』の連続は、計画的な尾行である可能性が高いです。",
            "別れの理由は何であれ、追うことは違法です。",
            "自分の感情の管理は、自分の責任です。",
        ],
        "risk_indicators": [
            "別れ後のエスカレーション",
            "被害者の新しい交際相手への攻撃",
            "自殺・危害の脅迫",
            "被害者の家族・子供への接近",
        ],
        "legal_articles": ["ストーカー規制法", "刑法222条（脅迫）", "刑法220条（監禁）"],
    },
    "cyber": {
        "label_ja": "サイバー犯罪",
        "label_en": "Cyber Crime",
        "psych_profile": {
            "core_traits": ["匿名性への依存", "共感能力の欠如", "優越感", "集団心理"],
            "attachment_style": "回避型",
            "common_disorders": ["ネット依存", "社会不安障害", "パーソナリティ障害"],
            "trigger_factors": ["標的の特定（容姿・思想）", "集団への帰属", "報酬（いいね・共有）"],
        },
        "behavior_patterns": [
            "匿名アカウントでの執拗な中傷",
            "複数アカウントでの集団攻撃",
            "被害者の個人情報の拡散（ドクシング）",
            "偽情報の作成・拡散",
        ],
        "tactics": {
            "dogpiling": "複数アカウントで同時攻撃",
            "doxxing": "個人情報の暴露",
            "gaslighting": "被害者の感覚を否定",
            "sealioning": "執拗な質問攻め",
        },
        "common_excuses": {
            "ただの冗談": "繰り返しの中傷は冗談ではなく、侮辱罪です。",
            "お前が悪い": "被害者の過失は、中傷の正当化になりません。",
            "デマでも誰かが言ってた": "拡散者にも拡散責任があります。",
            "匿名だからバレない": "IPアドレス・端末情報から特定は可能です。",
            "発言の自由": "発言の自由には責任が伴います。",
        },
        "counter_arguments": [
            "繰り返しの中傷は、日本の刑法230条・231条に該当します。",
            "被害者に過失があっても、中傷は別の犯罪です。",
            "デマの拡散も、名誉毀損の共同不法行為が成立します。",
            "技術的に、匿名からの特定は十分に可能です。",
            "発言の自由は、他人の権利を侵害する行為を保護しません。",
        ],
        "risk_indicators": [
            "被害者の個人情報の暴露",
            "就職先・学校への中傷拡散",
            "集団的・組織的な攻撃",
            "自殺教唆・助長",
        ],
        "legal_articles": ["刑法230条（侮辱）", "刑法231条（名誉毀損）", "特定電子メール法"],
    },
    "consumer_fraud": {
        "label_ja": "消費者被害・詐欺",
        "label_en": "Consumer Fraud",
        "psych_profile": {
            "core_traits": ["計算性", "共感能力の欠如", "金銭至上主義", "リスク無視"],
            "attachment_style": "回避型",
            "common_disorders": ["ギャンブル依存", "薬物依存", "反社会性パーソナリティ障害"],
            "trigger_factors": ["金銭需要", "被害者の弱み（高齢・孤独・知識不足）", "技術的優位性"],
        },
        "behavior_patterns": [
            "標的選定（高齢者・孤独・金銭的余裕あり）",
            "信頼関係構築（過度な親切・定期的接触）",
            "緊急性創出（『今だけ』『期限切れ』）",
            "回収困難化（振込先の複雑化・海外口座）",
        ],
        "tactics": {
            "phishing": "偽のメール・SMSで個人情報を騙取",
            "romance_scam": "恋愛関係を装って金銭を騙取",
            "investment_scam": "高額リターンを約束して投資を勧誘",
            "grandparent_scam": "孫を装って緊急金を要求",
        },
        "common_excuses": {
            "自分で選んだ": "被害者が18歳未満・精神的脆弱状態なら、同意能力に問題あり。",
            "お金を稼げて助けた": "搾取は援助ではありません。",
            "知らなかった": "常識的に知るべき事実の無知は免責になりません。",
            "被害者が儲け話に乗った": "儲け話に乗ることを装った詐欺は、被害者の過失ではなく加害者の計略です。",
        },
        "counter_arguments": [
            "被害者が同意したとしても、欺罔（ぎとう）による同意は無効です。",
            "金銭的利益を約束して搾取することは、刑法246条（詐欺罪）です。",
            "「知らなかった」は、確認義務があった場合免責になりません。",
            "被害者が「儲け話に乗った」のは、加害者が作った罠に落ちたからです。",
        ],
        "risk_indicators": [
            "被害者の銀行口座の異常な動き",
            "高齢者の孤立化",
            "加害者の複数被害者",
            "組織的・国際的な犯行",
        ],
        "legal_articles": ["刑法246条（詐欺）", "組織的犯罪処罰法", "消費者契約法"],
    },
    "chikan": {
        "label_ja": "痴漢・公共交通内性犯罪",
        "label_en": "Train / Public Transit Sexual Harassment",
        "psych_profile": {
            "core_traits": ["触物癖（フロッテュール）", "恋物癖", "共感能力の欠如", "匿名性依存"],
            "attachment_style": "回避型または混乱型",
            "common_disorders": ["性嗜好障害（触物癖）", "パーソナリティ障害", "社交不安障害"],
            "trigger_factors": ["混雑した公共交通", "被害者の孤立（逃げ場なし）", "通勤・通学時間帯"],
        },
        "behavior_patterns": [
            "混雑車両を狙う",
            "ドア際・座席間など逃げ場のない位置を選定",
            "短時間で実行し次の駅で離脱",
            "同じ路線・時間帯を繰り返す",
        ],
        "tactics": {
            "crowd_anonymity": "混雑と匿名性を盾に、被害者が声を上げにくい状況を悪用",
            "physical_trap": "ドア際や座席間で身体を固定し、逃げられない位置を作る",
            "quick_escape": "次の駅で即座に降り、別の車両に移動",
            "repeat_offense": "同じ駅・時間帯・路線を繰り返し、パターン化する",
        },
        "common_excuses": {
            "電車が混んでたから偶然": "混雑は痴漢の『方便』です。明確な触覚・圧力がかかっていたら、偶然ではありません。",
            "何もしてない、冤罪だ": "被害者がわざわざ騒ぐメリットはありません。女性が痴漢と認識した時点で、それは犯罪です。",
            "彼女が悪い、服がエロい": "服装は加害の理由になりません。痴漢は加害者の欲望の問題であり、被害者の服装とは無関係です。",
            "怒鳴るな、大げさだ": "被害者の恐怖・不快感の大きさは、被害者が決めます。加害者が『大げさ』と決めつける権利はありません。",
            "前科があるわけじゃない": "痴漢は常習犯が多く、多くの場合は初犯ではなく『初めて逮捕された』だけです。",
        },
        "counter_arguments": [
            "混雑は痴漢の『方便』であり、偶然の接触とは明確に区別できます。",
            "被害者が痴漢と認識した時点で、それは犯罪です。",
            "被害者の服装は、加害行為を正当化する理由にはなりません。",
            "被害者の不快感の大きさは、被害者が決めます。",
            "痴漢は再犯率が極めて高い犯罪です。",
        ],
        "risk_indicators": [
            "同じ路線・時間帯の繰り返し",
            "被害者への執拗な接近・追跡",
            "暴力エスカレーション（暴行に発展）",
            "複数被害者の存在",
        ],
        "legal_articles": ["刑法176条（強制わいせつ）", "迷惑防止条例", "鉄道営業法"],
    },
    "exposure": {
        "label_ja": "公然わいせつ・暴露狂",
        "label_en": "Indecent Exposure / Exhibitionism",
        "psych_profile": {
            "core_traits": ["露体癖（エキシビショニズム）", "被害者反応依存", "社会的コミュニケーション能力の欠如"],
            "attachment_style": "回避型",
            "common_disorders": ["露体症", "パーソナリティ障害", "うつ病", "社交不安障害"],
            "trigger_factors": ["被害者の驚き・恐怖反応", "匿名性・逃走可能性", "特定の場所・時間帯"],
        },
        "behavior_patterns": [
            "公園・駅・学校周辺・駐輪場など被害者が集まる場所を狙う",
            "車からの露出も多い",
            "被害者を選定して接近",
            "同じ場所・時間帯を繰り返す",
        ],
        "tactics": {
            "surprise_attack": "突然の露出で被害者を動けなくし、恐怖を与える",
            "car_escape": "車から露出し、すぐに逃走できるようにする",
            "child_targeting": "子供・青少年を標的にし、抵抗力のなさを悪用",
            "repeat_location": "同じ場所で繰り返し、パターン化する",
        },
        "common_excuses": {
            "着替え中だった": "公共の場で意図的に露出したことは『公然わいせつ』です。着替えの理由は成立しません。",
            "気づかなかった": "公園・道路等は常に人がいる可能性がある場所です。『気づかなかった』は免責になりません。",
            "子供だから何もわからない": "子供だからこそ、恐怖の影響は深刻です。児童への公然わいせつは重く処罰されます。",
            "大げさに取り上げるな": "被害者の恐怖・不快感の大きさは被害者が決めます。",
            "冤罪だ、服を直してただけ": "動作・場所・状況から、意図的な露出か偶発的な動作かは判断可能です。",
        },
        "counter_arguments": [
            "公共の場での露出は、『公然わいせつ』として処罰されます。",
            "『誰もいないと思った』は、公共の場では免責になりません。",
            "児童への公然わいせつは、成人より重く処罰されます。",
            "被害者の恐怖の大きさは、被害者が決めます。",
            "常習犯は同じ場所・時間帯を繰り返します。",
        ],
        "risk_indicators": [
            "同じ場所・時間帯の繰り返し",
            "子供・青少年への標的化",
            "被害者への執拗な接近",
            "暴力エスカレーション",
        ],
        "legal_articles": ["刑法174条（公然わいせつ）", "迷惑防止条例", "児童福祉法"],
    },
}


def profile_perpetrator(scenario: str) -> dict:
    """Return full perpetrator profile for a given scenario."""
    return PERPETRATOR_DB.get(scenario, {})


def analyze_excuses(scenario: str, excuses: list[str]) -> list[dict]:
    """Analyze perpetrator excuses and generate counter-arguments."""
    profile = PERPETRATOR_DB.get(scenario, {})
    common_excuses = profile.get("common_excuses", {})
    counter_args = profile.get("counter_arguments", [])
    results = []

    for excuse in excuses:
        excuse_clean = excuse.strip()
        matched = False
        for key, explanation in common_excuses.items():
            if key in excuse_clean or excuse_clean in key:
                results.append({
                    "excuse": excuse_clean,
                    "matched_pattern": key,
                    "perpetrator_psychology": explanation,
                    "counter_argument": counter_args[len(results) % len(counter_args)] if counter_args else "その言い訳は法律上正当化されません。",
                    "legal_basis": profile.get("legal_articles", []),
                })
                matched = True
                break
        if not matched:
            results.append({
                "excuse": excuse_clean,
                "matched_pattern": "未知のパターン",
                "perpetrator_psychology": "被害者責任転嫁または軽視の典型パターンです。",
                "counter_argument": counter_args[len(results) % len(counter_args)] if counter_args else "その言い訳は法律上正当化されません。",
                "legal_basis": profile.get("legal_articles", []),
            })
    return results


def generate_risk_assessment(scenario: str, victim_description: str = "") -> dict:
    """Generate risk assessment based on scenario and victim description."""
    profile = PERPETRATOR_DB.get(scenario, {})
    risk_indicators = profile.get("risk_indicators", [])
    risk_score = 0
    risk_factors = []

    # Simple keyword-based risk scoring
    danger_keywords = ["別れ", "武器", "殺す", "死", "子供", "家族", "職場", "自殺", "危害", "追う"]
    for kw in danger_keywords:
        if kw in victim_description:
            risk_score += 1
            risk_factors.append(kw)

    if risk_score >= 4:
        level = "HIGH"
        color = "🔴"
    elif risk_score >= 2:
        level = "MEDIUM"
        color = "🟡"
    else:
        level = "LOW"
        color = "🟢"

    return {
        "risk_level": level,
        "risk_score": risk_score,
        "risk_factors": risk_factors,
        "indicators": risk_indicators,
        "recommendation": "警察（110）へ即座連絡" if level == "HIGH" else "支援機関相談・証拠保全" if level == "MEDIUM" else "継続的モニタリング",
    }


def print_profile(scenario: str) -> None:
    """Pretty-print perpetrator profile."""
    profile = profile_perpetrator(scenario)
    if not profile:
        print(f"[error] Unknown scenario: {scenario}")
        return

    print(f"\n{'='*60}")
    print(f"加害者側写: {profile['label_ja']} ({profile['label_en']})")
    print(f"{'='*60}\n")

    print("【心理プロファイル】")
    for k, v in profile["psych_profile"].items():
        if isinstance(v, list):
            print(f"  {k}: {', '.join(v)}")
        else:
            print(f"  {k}: {v}")

    print("\n【行動パターン】")
    for p in profile["behavior_patterns"]:
        print(f"  • {p}")

    print("\n【支配戦術】")
    for tactic, desc in profile["tactics"].items():
        print(f"  • {tactic}: {desc}")

    print("\n【常用狡弁】")
    for excuse, analysis in profile["common_excuses"].items():
        print(f"  💬 {excuse}")
        print(f"     → {analysis}\n")

    print("【反論キット】")
    for counter in profile["counter_arguments"]:
        print(f"  ✅ {counter}")

    print("\n【リスク指標】")
    for ri in profile["risk_indicators"]:
        print(f"  ⚠️ {ri}")

    print(f"\n【関連法條】")
    print(f"  {', '.join(profile['legal_articles'])}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="LegalShield Perpetrator Profiler")
    parser.add_argument("--scenario", required=True, choices=list(PERPETRATOR_DB.keys()), help="Crime scenario")
    parser.add_argument("--excuses", default="", help="Space-separated perpetrator excuses")
    parser.add_argument("--victim-desc", default="", help="Short victim description for risk scoring")
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()

    print_profile(args.scenario)

    if args.excuses:
        excuse_list = [e.strip() for e in args.excuses.split("　") if e.strip()]
        print(f"\n{'='*60}")
        print(f"狡弁分析")
        print(f"{'='*60}")
        results = analyze_excuses(args.scenario, excuse_list)
        for r in results:
            print(f"\n💬 狡弁: {r['excuse']}")
            print(f"   パターン: {r['matched_pattern']}")
            print(f"   心理分析: {r['perpetrator_psychology']}")
            print(f"   ✅ 反論: {r['counter_argument']}")

    if args.victim_desc:
        print(f"\n{'='*60}")
        print(f"リスクアセスメント")
        print(f"{'='*60}")
        risk = generate_risk_assessment(args.scenario, args.victim_desc)
        print(f"リスクレベル: {risk['risk_level']}")
        print(f"リスクスコア: {risk['risk_score']}/10")
        print(f"検出要因: {', '.join(risk['risk_factors']) if risk['risk_factors'] else 'なし'}")
        print(f"推奨対応: {risk['recommendation']}")

    # Save JSON if requested
    if args.output:
        full_result = {
            "scenario": args.scenario,
            "profile": profile_perpetrator(args.scenario),
            "excuse_analysis": analyze_excuses(args.scenario, [e.strip() for e in args.excuses.split("　") if e.strip()]) if args.excuses else [],
            "risk_assessment": generate_risk_assessment(args.scenario, args.victim_desc) if args.victim_desc else {},
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(full_result, f, ensure_ascii=False, indent=2)
        print(f"\n[ok] Saved to {args.output}")


if __name__ == "__main__":
    main()
