"""LegalShield Victim Assistant — AI multi-role victim support engine.

Demonstrates the 5-role AI system:
  1. Emergency Responder
  2. Evidence Collector
  3. Legal Analyst (RAG retrieval)
  4. Strategy Simulator
  5. Referral Navigator

Usage:
  python victim_assistant.py --scenario "DV" --query "夫から暴力を受けています"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"


def load_vectors(path: Path) -> tuple[pd.DataFrame, np.ndarray]:
    df = pd.read_parquet(path)
    vecs = np.stack(df["vector"].values)
    return df, vecs


def search(query: str, model: SentenceTransformer, df: pd.DataFrame, vecs: np.ndarray, topk: int = 5):
    q_vec = model.encode([query])[0]
    sims = np.dot(vecs, q_vec) / (np.linalg.norm(vecs, axis=1) * np.linalg.norm(q_vec))
    df["score"] = sims
    return df.nlargest(topk, "score")


def emergency_responder(prefecture: str = "東京都") -> dict:
    """Role 1: Immediate safety + hotline routing."""
    hotlines_path = KNOWLEDGE / "seeds" / "national_hotlines.csv"
    hotlines = pd.read_csv(hotlines_path, encoding="utf-8-sig")
    relevant = hotlines[
        (hotlines["prefecture"] == "全国") | (hotlines["prefecture"] == prefecture)
    ]
    return {
        "role": "Emergency Responder",
        "urgency": "HIGH",
        "actions": [
            "If in immediate danger, call 110 or go to the nearest police station.",
            "Preserve evidence: do not delete messages, photos, or medical records.",
        ],
        "hotlines": relevant[["category", "name", "phone", "availability", "notes"]].to_dict("records"),
    }


def evidence_collector(case_type: str) -> dict:
    """Role 2: Evidence preservation checklist."""
    checklists = {
        "DV": [
            "Photos of injuries (with timestamp)",
            "Medical records / hospital receipts",
            "Threatening messages (LINE, email, SMS)",
            "Voice recordings (if legal in your prefecture)",
            "Witness statements",
            "Police consultation records",
            "Protection order application copies",
        ],
        "性暴力": [
            "Do NOT shower before medical examination",
            "Preserve clothing in paper bag",
            "Medical forensic examination at designated hospital",
            "SANE (Sexual Assault Nurse Examiner) kit if available",
            "Screenshots of communications",
            "Location/timeline documentation",
        ],
        "消費者被害": [
            "Contract documents",
            "Payment receipts / bank transfer records",
            "Product photos / serial numbers",
            "Advertising screenshots",
            "Communication logs with seller",
            "Witness statements from other victims",
        ],
        "職場": [
            "Work records / timesheets",
            "Emails / memos from employer",
            "Medical certificates for stress leave",
            "Union consultation records",
            "Power harassment diary (dated entries)",
            "Pay slips showing discrepancies",
        ],
        "児童虐待": [
            "Child's statements (recorded with consent)",
            "Photos of injuries / neglect conditions",
            "School records / teacher observations",
            "Medical examination records",
            "Previous agency reports",
            "Neighborhood witness accounts",
        ],
    }
    return {
        "role": "Evidence Collector",
        "case_type": case_type,
        "checklist": checklists.get(case_type, ["Document everything with dates and witnesses."]),
        "preservation_tip": "Store copies in 3 places: local encrypted drive, trusted friend, LegalShield vault.",
    }


def legal_analyst(query: str, model: SentenceTransformer) -> dict:
    """Role 3: RAG legal search."""
    # Search national laws
    elaws_path = KNOWLEDGE / "elaws_full_embedded.parquet"
    if not elaws_path.exists():
        return {"role": "Legal Analyst", "error": "elaws_full_embedded.parquet not found", "laws": [], "precedents": []}

    df_law, vecs_law = load_vectors(elaws_path)
    top_laws = search(query, model, df_law, vecs_law, topk=5)

    # Search unified knowledge for support context
    uni_path = KNOWLEDGE / "unified_knowledge_v2.parquet"
    df_uni, vecs_uni = load_vectors(uni_path)
    top_context = search(query, model, df_uni, vecs_uni, topk=5)

    return {
        "role": "Legal Analyst",
        "query": query,
        "relevant_laws": top_laws[["law_name", "article", "text", "score"]].to_dict("records"),
        "context_support": top_context[["source_type", "text", "score"]].to_dict("records"),
    }


def strategy_simulator(case_type: str, prefecture: str = "東京都") -> dict:
    """Role 4: Path comparison."""
    paths = {
        "DV": [
            {"path": "A. 刑事告訴", "target": "警察", "time": "1-6 months", "cost": "Free", "success": "60-70%", "pros": "Strongest deterrent, protection order possible", "cons": "Requires evidence, may escalate family conflict"},
            {"path": "B. 民事訴訟（損害賠償）", "target": "家庭裁判所/地裁", "time": "6-18 months", "cost": "¥300k-1M+", "success": "50-60%", "pros": "Compensation for damages", "cons": "High cost, long process"},
            {"path": "C. 民事保護命令", "target": "家庭裁判所", "time": "1-4 weeks", "cost": "Free (if waived)", "success": "80%+", "pros": "Fast, immediate protection", "cons": "Limited duration, no compensation"},
            {"path": "D. ADR（調停）", "target": "弁護士会/調停機構", "time": "1-3 months", "cost": "¥50k-200k", "success": "40-50%", "pros": "Confidential, less adversarial", "cons": "Non-binding, requires cooperation"},
        ],
        "性暴力": [
            {"path": "A. 刑事告訴", "target": "警察", "time": "6-24 months", "cost": "Free", "success": "30-40%", "pros": "Punishment, deterrence", "cons": "Traumatic process, low conviction rate"},
            {"path": "B. 民事損害賠償", "target": "地裁", "time": "12-36 months", "cost": "¥500k-2M", "success": "40-50%", "pros": "Compensation, lower burden of proof", "cons": "Expensive, confronting defendant"},
            {"path": "C. 性暴力救援センター支援", "target": "ワンストップ支援", "time": "Immediate", "cost": "Free", "success": "N/A", "pros": "Counseling, medical, legal aid", "cons": "No direct legal outcome"},
        ],
        "消費者被害": [
            {"path": "A. 消費者ホットライン通報", "target": "消費者庁", "time": "1-3 months", "cost": "Free", "success": "30-40%", "pros": "Administrative action possible", "cons": "No direct compensation"},
            {"path": "B. 小額訴訟", "target": "簡易裁判所", "time": "2-6 months", "cost": "¥20k-50k", "success": "60-70%", "pros": "Low cost, fast", "cons": "Limited to ¥1.4M claim"},
            {"path": "C. ADR / 消費者団体", "target": "国民生活センター", "time": "1-6 months", "cost": "Free-¥30k", "success": "50-60%", "pros": "Expert assistance, mediation", "cons": "Non-binding"},
        ],
        "職場": [
            {"path": "A. 労働基準監督署申告", "target": "労基署", "time": "1-6 months", "cost": "Free", "success": "50-60%", "pros": "Administrative enforcement", "cons": "Retaliation risk"},
            {"path": "B. 民事訴訟（損害賠償）", "target": "裁判所", "time": "6-24 months", "cost": "¥300k-1M", "success": "40-50%", "pros": "Compensation", "cons": "High cost, may affect career"},
            {"path": "C. 労働審判", "target": "労働審判", "time": "3-6 months", "cost": "Free-¥100k", "success": "60-70%", "pros": "Faster than civil suit", "cons": "Limited remedies"},
        ],
        "児童虐待": [
            {"path": "A. 児童相談所通報", "target": "児童相談所", "time": "Immediate", "cost": "Free", "success": "70-80%", "pros": "Child protection priority", "cons": "Family disruption"},
            {"path": "B. 刑事告訴", "target": "警察", "time": "3-12 months", "cost": "Free", "success": "50-60%", "pros": "Punishment", "cons": "Child testimony may be traumatic"},
            {"path": "C. 家庭裁判所（親権停止等）", "target": "家庭裁判所", "time": "1-6 months", "cost": "Free (if waived)", "success": "60-70%", "pros": "Custody change possible", "cons": "Adversarial process"},
        ],
    }
    return {
        "role": "Strategy Simulator",
        "case_type": case_type,
        "prefecture": prefecture,
        "paths": paths.get(case_type, [{"path": "Consult local bar association for case-specific advice."}]),
        "recommendation": "Combine A + C for fastest protection with lowest cost." if case_type == "DV" else "Consult free hotline first before any formal action.",
    }


def referral_navigator(case_type: str, prefecture: str = "東京都") -> dict:
    """Role 5: Match nearest support organizations."""
    # Load seeds
    seeds = []
    for csv_name in ["support_centers_seed.csv", "ngo_seed.csv", "bar_associations.csv"]:
        path = KNOWLEDGE / "seeds" / csv_name
        if path.exists():
            df = pd.read_csv(path, encoding="utf-8-sig")
            df["source"] = csv_name.replace(".csv", "")
            seeds.append(df)

    if seeds:
        all_orgs = pd.concat(seeds, ignore_index=True)
        # Filter by prefecture if available
        if "prefecture" in all_orgs.columns:
            matched = all_orgs[all_orgs["prefecture"] == prefecture]
        else:
            matched = all_orgs
    else:
        matched = pd.DataFrame()

    return {
        "role": "Referral Navigator",
        "case_type": case_type,
        "prefecture": prefecture,
        "matched_organizations": matched.to_dict("records") if not matched.empty else [],
        "national_hotlines": [
            {"name": "警察", "phone": "110", "for": "緊急事態・犯罪通報"},
            {"name": "法テラス", "phone": "050-5538-5555", "for": "法律相談"},
            {"name": "消費者ホットライン", "phone": "188", "for": "消費者被害"},
            {"name": "いのちの電話", "phone": "0120-783-556", "for": "自殺予防"},
        ],
    }


def run_assistant(scenario: str, query: str, prefecture: str = "東京都") -> dict:
    print(f"\n{'='*60}")
    print(f"LegalShield Victim Assistant")
    print(f"Scenario: {scenario}")
    print(f"Query: {query}")
    print(f"Prefecture: {prefecture}")
    print(f"{'='*60}")

    # Load model once
    print("\n[Loading AI model...]")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # 5 roles
    r1 = emergency_responder(prefecture)
    r2 = evidence_collector(scenario)
    r3 = legal_analyst(query, model)
    r4 = strategy_simulator(scenario, prefecture)
    r5 = referral_navigator(scenario, prefecture)

    report = {
        "meta": {"scenario": scenario, "query": query, "prefecture": prefecture},
        "emergency_responder": r1,
        "evidence_collector": r2,
        "legal_analyst": r3,
        "strategy_simulator": r4,
        "referral_navigator": r5,
    }
    return report


def print_report(report: dict) -> None:
    print("\n" + "─" * 60)
    print("🚨 1. EMERGENCY RESPONDER")
    print("─" * 60)
    for action in report["emergency_responder"]["actions"]:
        print(f"  → {action}")
    print("\n  📞 Hotlines:")
    for h in report["emergency_responder"]["hotlines"][:5]:
        print(f"     [{h['category']}] {h['name']}: {h['phone']} ({h['availability']})")

    print("\n" + "─" * 60)
    print("📁 2. EVIDENCE COLLECTOR")
    print("─" * 60)
    print(f"  Case type: {report['evidence_collector']['case_type']}")
    print(f"  Tip: {report['evidence_collector']['preservation_tip']}")
    print("  Checklist:")
    for item in report["evidence_collector"]["checklist"]:
        print(f"    □ {item}")

    print("\n" + "─" * 60)
    print("⚖️  3. LEGAL ANALYST")
    print("─" * 60)
    if "error" in report["legal_analyst"]:
        print(f"  Error: {report['legal_analyst']['error']}")
    else:
        print(f"  Query: {report['legal_analyst']['query']}")
        print("\n  📚 Relevant Laws:")
        for law in report["legal_analyst"]["relevant_laws"]:
            print(f"     • {law['law_name']} {law['article']} (score: {law['score']:.3f})")
            text_preview = law['text'][:80].replace('\n', ' ')
            print(f"       {text_preview}...")

    print("\n" + "─" * 60)
    print("🧭 4. STRATEGY SIMULATOR")
    print("─" * 60)
    print(f"  Recommendation: {report['strategy_simulator']['recommendation']}")
    print("\n  Path comparison:")
    for p in report["strategy_simulator"]["paths"]:
        print(f"    {p['path']}")
        print(f"      Target: {p['target']} | Time: {p['time']} | Cost: {p['cost']} | Success: {p['success']}")
        print(f"      Pros: {p['pros']}")
        print(f"      Cons: {p['cons']}")

    print("\n" + "─" * 60)
    print("🗺️  5. REFERRAL NAVIGATOR")
    print("─" * 60)
    print("  📞 National Hotlines:")
    for h in report["referral_navigator"]["national_hotlines"]:
        print(f"     {h['name']}: {h['phone']} — {h['for']}")
    if report["referral_navigator"]["matched_organizations"]:
        print("\n  🏢 Local Organizations:")
        for org in report["referral_navigator"]["matched_organizations"][:5]:
            print(f"     • {org}")
    else:
        print("\n  (No local organizations in seed data for this prefecture)")

    print("\n" + "=" * 60)
    print("LegalShield Action Plan Generated.")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="LegalShield Victim Assistant")
    parser.add_argument("--scenario", default="DV", choices=["DV", "性暴力", "消費者被害", "職場", "児童虐待"])
    parser.add_argument("--query", default="配偶者から暴力を受けています", help="Situation description")
    parser.add_argument("--prefecture", default="東京都", help="Your prefecture")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    report = run_assistant(args.scenario, args.query, args.prefecture)

    if args.json:
        # Remove vectors from JSON output (too large)
        safe_report = json.loads(json.dumps(report, default=str))
        print(json.dumps(safe_report, ensure_ascii=False, indent=2))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
