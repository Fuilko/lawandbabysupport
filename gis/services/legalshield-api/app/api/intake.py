"""POST /api/v1/legalshield/intake

Rule-based triage: accepts a 6-question intake form, detects the most
likely problem category, and returns a tier 1-5 ranked recommendation
plan with hotline numbers, scripts, document checklists, and next-tier
escalation hints.

Design notes
────────────
* No LLM in this version — pure rule-based keyword/answer mapping so we
  can ship an MVP and let the user observe failure modes before plugging
  in an SLM.
* Anonymous: only an optional client_hash header is recorded; raw text is
  stored only if `consent_store_text` is true (Tier 1 of the 5-tier
  consent ladder).
* If Q1 indicates immediate danger → response upgrades to emergency mode
  with the urgent_hotline pinned to position 0.
* Saves an `intake_session` row when the DB is reachable; failure here
  must NOT break the user-facing recommendation (graceful degradation).
"""
from __future__ import annotations

import logging
import re
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

router = APIRouter()
logger = logging.getLogger("legalshield.intake")


# ─── request / response schemas ──────────────────────────────────────


CategoryCode = Literal[
    "dv", "stalking", "sexual_violence", "child_abuse",
    "elder_abuse", "school_bullying", "workplace_harassment",
    "labor_violation", "foreign_worker", "consumer_fraud",
    "product_defect", "admin_grievance",
]

Q2Choice = Literal[
    "interpersonal_violence",  # 人間関係の暴力
    "work",                    # 仕事の問題
    "product_service",         # 製品・サービス
    "admin_welfare",           # 行政・福祉
    "child_school",            # 子ども・学校
    "other",
]

Q3Choice = Literal["today", "days", "weeks", "months_plus"]

Q5Choice = Literal["police", "lawyer", "npo", "family_friends", "none"]

Q6Choice = Literal["info", "listen", "act_with_me", "legal_resolution"]


class IntakeRequest(BaseModel):
    # Q1: immediate danger
    immediate_danger: bool = Field(..., description="Q1: 命の危険切迫か")
    # Q2: closest category bucket
    bucket: Q2Choice = Field(..., description="Q2: 困りごとのバケット")
    # Q3: duration
    duration: Q3Choice = Field(..., description="Q3: いつ頃から続いているか")
    # Q4: optional free text
    free_text: Optional[str] = Field(
        None, max_length=2000, description="Q4: 自由記述（任意）"
    )
    # Q5: prior consultations
    prior_consult: Optional[Q5Choice] = Field(
        None, description="Q5: これまでの相談先"
    )
    # Q6: what they want
    want: Optional[Q6Choice] = Field(None, description="Q6: 一番欲しいもの")

    # context (optional, governs ranking)
    category_hint: Optional[CategoryCode] = Field(
        None, description="Operator-mode: skip detection by passing category directly"
    )
    language: str = Field("ja", description="UI language: ja/en/zh/ko/vi/pt")
    prefecture_code: Optional[str] = Field(None, max_length=2)
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)

    # consent toggles (5-tier ladder)
    consent_store_text: bool = Field(False, description="Tier 1: store redacted text")
    consent_share_city: bool = Field(False, description="Tier 2: share city-level location")


# ─── category detection (rule-based) ─────────────────────────────────


# Keywords per category. All Japanese; the front-end can preprocess for
# other languages or call this with category_hint after its own routing.
# Keep this conservative — false negatives are OK (we fall back to the
# bucket-mapping table below), false positives can route someone to a
# wrong hotline.
KEYWORDS: dict[CategoryCode, tuple[str, ...]] = {
    "dv":              ("dv", "ｄｖ", "配偶者", "パートナー", "夫", "妻", "彼氏", "彼女", "殴", "蹴", "殺すと", "怖い"),
    "stalking":        ("ストーカー", "つきまと", "待ち伏せ", "尾行", "盗撮", "盗聴", "監視され"),
    "sexual_violence": ("性犯罪", "性暴力", "レイプ", "強姦", "わいせつ", "痴漢", "盗撮", "リベンジポルノ"),
    "child_abuse":     ("児童虐待", "子ども虐待", "ネグレクト", "育児放棄", "親に殴", "親が怖", "189"),
    "elder_abuse":     ("高齢者虐待", "親の介護", "祖父", "祖母", "デイサービス", "施設で虐待"),
    "school_bullying": ("いじめ", "イジメ", "学校", "クラスメイト", "不登校", "スクール"),
    "workplace_harassment": ("パワハラ", "セクハラ", "マタハラ", "ハラスメント", "上司から", "同僚から", "職場で"),
    "labor_violation": ("残業代", "未払い", "サービス残業", "解雇", "クビ", "労基", "ブラック企業", "退職"),
    "foreign_worker":  ("技能実習", "特定技能", "在留資格", "ビザ", "パスポート取り上げ", "外国人"),
    "consumer_fraud":  ("詐欺", "騙され", "振り込め", "ロマンス詐欺", "投資", "サブスク", "クーリングオフ"),
    "product_defect":  ("欠陥", "故障", "リコール", "ＰＬ", "pl法", "製造物責任", "事故", "ドローン"),
    "admin_grievance": ("行政", "市役所", "区役所", "児相", "生活保護", "家族分離", "在留不許可"),
}

# Coarse bucket → likely categories (fallback when keywords don't match).
# Order matters: first item is the default for that bucket.
BUCKET_MAP: dict[Q2Choice, tuple[CategoryCode, ...]] = {
    "interpersonal_violence": ("dv", "stalking", "sexual_violence"),
    "work":                   ("workplace_harassment", "labor_violation", "foreign_worker"),
    "product_service":        ("consumer_fraud", "product_defect"),
    "admin_welfare":          ("admin_grievance", "elder_abuse"),
    "child_school":           ("school_bullying", "child_abuse"),
    "other":                  ("admin_grievance",),
}


def detect_category(req: IntakeRequest) -> tuple[CategoryCode, float, str]:
    """Return (category, confidence 0..1, reason)."""
    if req.category_hint:
        return req.category_hint, 1.0, "operator_hint"

    text_blob = (req.free_text or "").lower()
    scores: dict[CategoryCode, int] = {}
    for cat, kws in KEYWORDS.items():
        hit = sum(1 for kw in kws if kw.lower() in text_blob)
        if hit:
            scores[cat] = hit

    if scores:
        best = max(scores.items(), key=lambda kv: kv[1])
        confidence = min(0.95, 0.5 + 0.15 * best[1])
        return best[0], confidence, f"keyword_hits={best[1]}"

    # fallback: bucket-mapping default
    fallback = BUCKET_MAP[req.bucket][0]
    return fallback, 0.45, f"bucket_default:{req.bucket}"


# ─── trigger resolution ──────────────────────────────────────────────


def derive_triggers(req: IntakeRequest) -> set[str]:
    """Derive trigger_condition tags from the intake answers.

    The category_routing table uses 'always' (always shown) plus optional
    conditional triggers like 'if_immediate_danger', 'if_evidence_strong',
    'if_money_lost_high', etc. We promote routes whose trigger matches.
    """
    triggers: set[str] = {"always"}
    if req.immediate_danger:
        triggers.add("if_immediate_danger")
    if req.duration in ("weeks", "months_plus"):
        triggers.add("if_evidence_strong")
    if req.prior_consult in ("lawyer", "npo"):
        # User has already consulted — they're escalation-ready
        triggers.add("if_evidence_strong")
    if req.want == "legal_resolution":
        triggers.add("if_money_lost_high")
        triggers.add("if_evidence_strong")
    return triggers


# ─── scoring ─────────────────────────────────────────────────────────


def score_route(route: dict, triggers: set[str], req: IntakeRequest) -> float:
    """Final score = weight × trigger-match × language × want-bias."""
    score = float(route["weight"])

    # trigger match
    tc = route["trigger_condition"]
    if tc == "always":
        pass  # neutral
    elif tc in triggers:
        score *= 1.20  # promotion
    else:
        score *= 0.50  # demotion but not exclusion

    # what-they-want bias
    if req.want == "info" and route["org_kind"] == "hotline":
        score *= 1.10
    if req.want == "listen" and route["org_kind"] in ("hotline", "npo"):
        score *= 1.10
    if req.want == "act_with_me" and route["org_kind"] in ("npo", "admin_center"):
        score *= 1.10
    if req.want == "legal_resolution" and route["org_kind"] in ("bar_assoc", "court"):
        score *= 1.15

    # language: ja routes are always ja-capable; for other langs we boost
    # foreign_worker hotline patterns slightly.
    if req.language != "ja" and "多言語" in (route.get("notes_ja") or ""):
        score *= 1.15

    return round(score, 4)


# ─── PII redaction (very light, server-side safety net) ─────────────


_PII_PATTERNS = [
    (re.compile(r"\d{3}-?\d{4}-?\d{4}"), "[電話番号]"),
    (re.compile(r"\d{2,4}-?\d{2,4}-?\d{3,4}"), "[電話番号]"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[メール]"),
    (re.compile(r"https?://\S+"), "[URL]"),
]


def redact(s: Optional[str]) -> Optional[str]:
    if not s:
        return s
    out = s
    for pat, rep in _PII_PATTERNS:
        out = pat.sub(rep, out)
    return out


# ─── endpoint ────────────────────────────────────────────────────────


@router.post("/intake", summary="6-question intake → tier 1-5 recommendation")
async def intake(
    req: IntakeRequest,
    x_client_hash: Optional[str] = Header(None, description="Opaque anonymous client identifier"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    # 1. detect category
    category, confidence, reason = detect_category(req)

    # 2. derive triggers
    triggers = derive_triggers(req)

    # 3. fetch routing rows for this category
    routing_sql = text(
        """
        SELECT id, tier, org_kind, org_name_pattern, weight,
               trigger_condition, what_to_say_ja, documents_needed_ja,
               expected_outcome_ja, next_tier_if_ja, notes_ja
        FROM legalshield.category_routing
        WHERE category_code = :code
        ORDER BY tier, weight DESC
        """
    )
    routes = [
        dict(r)
        for r in (
            await session.execute(routing_sql, {"code": category})
        ).mappings().all()
    ]

    # 4. score
    for r in routes:
        r["score"] = score_route(r, triggers, req)

    # 5. group by tier, ranked within each tier
    by_tier: dict[int, list[dict]] = {}
    for r in routes:
        by_tier.setdefault(int(r["tier"]), []).append(r)
    for t in by_tier:
        by_tier[t].sort(key=lambda x: x["score"], reverse=True)

    # 6. emergency mode upgrade
    cat_meta = (
        await session.execute(
            text(
                """
                SELECT name_ja, severity_default, urgent_hotline
                FROM legalshield.problem_category
                WHERE code = :c
                """
            ),
            {"c": category},
        )
    ).mappings().first()

    is_emergency = (
        req.immediate_danger
        or (cat_meta and cat_meta["severity_default"] == "critical")
    )

    # 7. persist intake_session (best-effort, graceful on failure)
    session_id: Optional[str] = None
    try:
        ins = text(
            """
            INSERT INTO legalshield.intake_session
              (client_hash, detected_category, detected_severity,
               detected_tags, language, prefecture_code,
               raw_text_consent, raw_text_redacted,
               llm_model, llm_confidence,
               recommendation_json)
            VALUES
              (:hash, :cat, :sev,
               :tags, :lang, :pref,
               :consent, :red,
               'rule_based_v1', :conf,
               :rec_json::jsonb)
            RETURNING id::text
            """
        )
        session_id = (
            await session.execute(
                ins,
                {
                    "hash": x_client_hash,
                    "cat": category,
                    "sev": cat_meta["severity_default"] if cat_meta else "medium",
                    "tags": list(triggers),
                    "lang": req.language,
                    "pref": req.prefecture_code,
                    "consent": req.consent_store_text,
                    "red": redact(req.free_text) if req.consent_store_text else None,
                    "conf": confidence,
                    "rec_json": _json_of(by_tier),
                },
            )
        ).scalar_one()
        await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("intake_session insert failed: %r — returning recs anyway", exc)
        await session.rollback()

    # 8. build response
    return {
        "session_id": session_id,
        "detection": {
            "category": category,
            "category_name_ja": cat_meta["name_ja"] if cat_meta else None,
            "severity": cat_meta["severity_default"] if cat_meta else None,
            "confidence": confidence,
            "reason": reason,
            "triggers_matched": sorted(triggers),
        },
        "emergency": {
            "is_emergency": is_emergency,
            "urgent_hotline": cat_meta["urgent_hotline"] if cat_meta else None,
            "message_ja": (
                "今すぐ身の安全を確保してください。下の番号にすぐ電話してください。"
                if is_emergency
                else None
            ),
        },
        "recommendations": {
            "tier_count": len(by_tier),
            "tiers": [
                {"tier": t, "routes": by_tier[t]}
                for t in sorted(by_tier.keys())
            ],
        },
        "disclaimer_ja": (
            "本サービスは一般的な法律情報・窓口案内を提供するものであり、"
            "特定事案に対する法的助言ではありません。"
            "最終的なご判断は弁護士など専門家にご相談ください。"
        ),
    }


def _json_of(by_tier: dict[int, list[dict]]) -> str:
    """JSON-serialize the recommendation, dropping non-serializable types."""
    import json
    return json.dumps(
        {
            str(t): [
                {k: v for k, v in r.items() if k != "id"}
                for r in routes
            ]
            for t, routes in by_tier.items()
        },
        ensure_ascii=False,
        default=str,
    )
