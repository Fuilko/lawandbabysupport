"""
Tier Decision Engine v0
========================
インシデント信号から「対応 Tier」を分類する保守的ルールエンジン。

設計原則 (EXPANSION_AND_DISPATCH_DESIGN_20260520.md Part C-3 準拠):
  1. AI 単独で Tier 1 判定しない (誤判定は人命に関わるため二重チェック)
  2. False positive 許容 (Tier 高めに振る) / False negative 厳禁
  3. 個情法 27 条 1 項 2 号「人の生命保護」例外を発動するのは Tier 1 のみ
  4. 全判定にログ + 監査ID付与 (中央監視で再現可能に)
  5. ユーザーには 30 秒キャンセル猶予 (誤発報対応)

依存: 標準ライブラリのみ。Pydantic 等は呼出側で。
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("dispatch.tier_engine")


# ---------------------------------------------------------------------------
# Tier 定義
# ---------------------------------------------------------------------------


class Tier(str, Enum):
    """対応 Tier。値は API レスポンスの文字列。"""

    TIER_1_LIFE = "tier1_life"           # 生命危険・直前 → 110 並行通知, 個情法例外発動
    TIER_2_URGENT = "tier2_urgent"       # 緊急・物理脅威 → NPO 緊急 + 弁護士オンコール
    TIER_3_CONSULT = "tier3_consult"     # 通常相談 → ユーザー選択型マッチング
    TIER_0_INFO = "tier0_info"           # 情報提供のみ → セルフサービス


# Tier ごとの推奨アクション (Dispatcher が参照)
TIER_ACTIONS: dict[Tier, dict[str, Any]] = {
    Tier.TIER_1_LIFE: {
        "call_110": True,
        "notify_npos": True,
        "npo_radius_km": 10,
        "npo_count": 3,
        "user_consent_required": False,   # 個情法 27-1-2 例外
        "log_emergency_override": True,
        "post_notify_user_hours": 24,
        "cancel_grace_sec": 30,
    },
    Tier.TIER_2_URGENT: {
        "call_110": False,
        "notify_npos": True,
        "npo_radius_km": 20,
        "npo_count": 3,
        "attorney_oncall": True,
        "attorney_radius_km": 50,
        "user_consent_required": True,
        "cancel_grace_sec": 30,
    },
    Tier.TIER_3_CONSULT: {
        "call_110": False,
        "notify_npos": False,
        "present_candidates_to_user": True,
        "candidate_radius_km": 30,
        "candidate_count": 10,
        "user_consent_required": True,
        "cancel_grace_sec": 0,
    },
    Tier.TIER_0_INFO: {
        "self_service_only": True,
        "user_consent_required": False,
        "cancel_grace_sec": 0,
    },
}


# ---------------------------------------------------------------------------
# Incident 信号
# ---------------------------------------------------------------------------


@dataclass
class IncidentSignal:
    """インシデント分類に使う観測信号。

    以下は **すべて任意フィールド** だが、判定に使われる信号は
    クライアント (iOS) 側で明示的に opt-in したもののみ送信する。
    """

    # ユーザーの明示的アクション
    user_pressed_panic_button: bool = False
    user_explicit_tier_request: Optional[Tier] = None  # 「ユーザーが明示的に呼んだ」場合は最優先

    # 自動検出 (端末側 ML / センサー由来)
    audio_screaming_detected: bool = False
    audio_aggressive_speech: bool = False
    heart_rate_bpm: Optional[int] = None
    gps_speed_kmh: Optional[float] = None
    location_marked_unsafe: bool = False   # ユーザー事前登録の危険エリア

    # テキスト由来 (相談文・通報メモから)
    text_weapon_keyword: bool = False
    text_threat_imminent: bool = False
    text_suicide_intent: bool = False
    text_minor_involved: bool = False

    # 文脈
    time_local_hour: Optional[int] = None   # 0-23 (深夜帯はリスク上昇)
    repeat_offender_history: bool = False

    # 任意の生データ (監査用)
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class TierDecision:
    """Tier 判定の結果。"""

    incident_id: str
    tier: Tier
    confidence: str                    # 'high' | 'medium' | 'low'
    reasons: list[str]
    triggered_flags: list[str]
    requires_human_review: bool
    actions: dict[str, Any]
    decided_at: str
    grace_period_sec: int

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["tier"] = self.tier.value
        return d


# ---------------------------------------------------------------------------
# 判定ロジック
# ---------------------------------------------------------------------------


def _check_tier_1(sig: IncidentSignal) -> tuple[bool, list[str]]:
    """Tier 1 (生命危険) 判定。**保守的に true へ寄せる** が、再現性のあるフラグのみ。"""
    flags: list[str] = []
    if sig.user_pressed_panic_button:
        flags.append("panic_button")
    if sig.text_weapon_keyword:
        flags.append("weapon")
    if sig.audio_screaming_detected:
        flags.append("scream")
    if sig.text_suicide_intent:
        flags.append("suicide_intent")
    # 心拍数 + 高速移動 = 逃走中の可能性
    if (sig.heart_rate_bpm or 0) >= 130 and (sig.gps_speed_kmh or 0) >= 8:
        flags.append("flee_pattern")
    if sig.user_explicit_tier_request == Tier.TIER_1_LIFE:
        flags.append("user_explicit_tier1")
    return (len(flags) > 0, flags)


def _check_tier_2(sig: IncidentSignal) -> tuple[bool, list[str]]:
    """Tier 2 (緊急・物理脅威)。"""
    flags: list[str] = []
    if sig.text_threat_imminent:
        flags.append("threat_imminent")
    if sig.location_marked_unsafe:
        flags.append("unsafe_location")
    if sig.audio_aggressive_speech:
        flags.append("aggressive_speech")
    if sig.repeat_offender_history and (sig.text_threat_imminent or sig.audio_aggressive_speech):
        flags.append("repeat_offender_active")
    if sig.text_minor_involved and (sig.text_threat_imminent or sig.audio_aggressive_speech):
        # 児童虐待防止法 6 条: 児童虐待を受けたと「思われる」児童発見は通告対象
        flags.append("minor_involved")
    if sig.user_explicit_tier_request == Tier.TIER_2_URGENT:
        flags.append("user_explicit_tier2")
    return (len(flags) > 0, flags)


def _confidence(triggered: list[str], tier: Tier) -> str:
    """フラグ数 + フラグ種別から信頼度を粗く決める。"""
    if not triggered:
        return "high" if tier == Tier.TIER_3_CONSULT else "low"
    strong_signals = {"panic_button", "weapon", "user_explicit_tier1", "user_explicit_tier2", "suicide_intent"}
    n_strong = sum(1 for f in triggered if f in strong_signals)
    if n_strong >= 1 and len(triggered) >= 2:
        return "high"
    if n_strong >= 1 or len(triggered) >= 2:
        return "medium"
    return "low"


def classify(sig: IncidentSignal, incident_id: Optional[str] = None) -> TierDecision:
    """インシデント信号 → Tier 判定。

    判定優先度:
      1. ユーザー明示要求 (TIER_1_LIFE) は最優先 = false negative 防止
      2. Tier 1 フラグあり → TIER_1_LIFE
      3. Tier 2 フラグあり → TIER_2_URGENT
      4. それ以外 → TIER_3_CONSULT
    """
    iid = incident_id or f"inc_{uuid.uuid4().hex[:12]}"
    reasons: list[str] = []

    # まず Tier 1 判定 (人命優先)
    is_t1, t1_flags = _check_tier_1(sig)
    if is_t1:
        tier = Tier.TIER_1_LIFE
        flags = t1_flags
        reasons.append("tier1 flags triggered")
        # AI 単独で判定不可フラグ: panic_button / user_explicit を含まない場合は human_review 必須
        purely_ai_signals = {"scream", "flee_pattern"}
        requires_human = all(f in purely_ai_signals for f in flags)
        if requires_human:
            reasons.append("AI-only signals; human review required before life-protection override")
    else:
        is_t2, t2_flags = _check_tier_2(sig)
        if is_t2:
            tier = Tier.TIER_2_URGENT
            flags = t2_flags
            reasons.append("tier2 flags triggered")
            requires_human = False
        else:
            tier = Tier.TIER_3_CONSULT
            flags = []
            reasons.append("no urgent signals; routing to standard consultation")
            requires_human = False

    confidence = _confidence(flags, tier)
    actions = dict(TIER_ACTIONS[tier])  # copy

    # 深夜帯 (22:00-05:00) は Tier 上げる調整 (Tier 3 → 2 の境界のみ)
    if (
        tier == Tier.TIER_3_CONSULT
        and sig.time_local_hour is not None
        and (sig.time_local_hour >= 22 or sig.time_local_hour < 5)
        and (sig.text_threat_imminent or sig.location_marked_unsafe)
    ):
        tier = Tier.TIER_2_URGENT
        actions = dict(TIER_ACTIONS[tier])
        reasons.append("late-night escalation to tier2")
        flags.append("late_night_context")

    decision = TierDecision(
        incident_id=iid,
        tier=tier,
        confidence=confidence,
        reasons=reasons,
        triggered_flags=flags,
        requires_human_review=requires_human,
        actions=actions,
        decided_at=datetime.now(timezone.utc).isoformat(),
        grace_period_sec=int(actions.get("cancel_grace_sec", 0)),
    )
    logger.info(
        "tier_decision id=%s tier=%s confidence=%s flags=%s human_review=%s",
        iid, tier.value, confidence, flags, requires_human,
    )
    return decision


# ---------------------------------------------------------------------------
# CLI / smoke test
# ---------------------------------------------------------------------------

def _demo() -> None:
    cases: list[tuple[str, IncidentSignal]] = [
        ("①パニックボタン",
         IncidentSignal(user_pressed_panic_button=True)),
        ("②深夜の脅迫テキスト",
         IncidentSignal(text_threat_imminent=True, time_local_hour=2)),
        ("③心拍+高速移動 (AI のみ)",
         IncidentSignal(heart_rate_bpm=145, gps_speed_kmh=12)),
        ("④通常相談",
         IncidentSignal(time_local_hour=14)),
        ("⑤未成年+加害者リピータ",
         IncidentSignal(text_minor_involved=True, text_threat_imminent=True, repeat_offender_history=True)),
        ("⑥ユーザー明示 Tier1",
         IncidentSignal(user_explicit_tier_request=Tier.TIER_1_LIFE)),
        ("⑦自殺念慮",
         IncidentSignal(text_suicide_intent=True)),
    ]
    import json
    for label, sig in cases:
        d = classify(sig)
        print(f"\n=== {label} ===")
        print(json.dumps(d.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    _demo()
