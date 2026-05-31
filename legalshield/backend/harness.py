"""
LegalShield Anti-Hallucination Harness — L1〜L7 実装

AGENT_SKILL_BOUND_DESIGN.md (docs/AGENT_SKILL_BOUND_DESIGN.md) の設計を
バックエンドで実装するモジュール。法律 AI が「DB を参照せず幻覚で自信満々に
回答する」問題を *構造的に* 防止する。

設計原則（同設計書 §1）:
  - ゼロ幻覚は不可能 → 「可検証幻覚」を目指す（検出・可視化・追跡）
  - 「知らない」を許容する出力スキーマ
  - 構造的拘束 > Prompt 拘束（retrieval gate / source-tag / cross-check を強制）

パイプライン（同設計書 §2）:
  L1 Intent & Risk Classifier
  L2 Mandatory Retrieval Gate
  L3 Variable-loaded Reasoning（本実装では context-pack の最小版）
  L4 Constrained Generation（source-tag 付き / refusal-aware）
  L5 Self-verification & Cross-check（claim 抽出 / retrieval match / judge）
  L6 Transparency payload（source tag / confidence / risk badge / lawyer trigger）
  L7 Audit Log（SHA-256 chain）

依存は *注入* する設計（循環 import 回避 + オフラインテスト可能）:
  - retrieve_precedents(question, top_k) -> list[Source]
  - retrieve_statutes(question, top_k)   -> list[Source]
  - llm_chat(system, user, temperature)  -> str
  - judge_chat(system, user, temperature)-> str  (任意、独立 model)

api.py がこれらの callable を実体に束ねて `/rag/answer` で公開する。
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal, Optional

logger = logging.getLogger("legalshield.harness")

HARNESS_VERSION = "1.0"

# 型エイリアス
ClaimType = Literal["factual", "strategic", "opinion", "procedural"]
RiskClass = Literal["low", "med", "high", "irreversible"]
Venue = Literal["consult", "adr", "litigation", "emergency"]

LlmChat = Callable[[str, str, float], str]
RetrieveFn = Callable[[str, int], "list[Source]"]


# ============================================================================
# データ構造
# ============================================================================

@dataclass
class Source:
    """L2 で取得した根拠 1 件。provenance / trust を必ず保持する。"""
    id: str                       # "S1", "S2" ... harness が連番付与
    kind: str                     # precedent / statute / partner / user_upload / external_ai
    text: str
    score: float                  # 距離（小さいほど近い）または類似度
    trust: str = "high"           # high / medium / low / quarantined
    provenance: str = "internal_kb"
    citation: str = ""            # 人間可読の出典ラベル（事件番号・条文番号等）
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "trust": self.trust,
            "provenance": self.provenance,
            "citation": self.citation,
            "excerpt": self.text[:400],
            "score": round(float(self.score), 4),
        }


@dataclass
class QueryIntent:
    claim_type: ClaimType
    risk_class: RiskClass
    venue: Venue
    domain: str
    requires_external_verify: bool
    requires_lawyer: bool
    reasons: list[str] = field(default_factory=list)

    def to_public(self) -> dict[str, Any]:
        return {
            "claim_type": self.claim_type,
            "risk_class": self.risk_class,
            "venue": self.venue,
            "domain": self.domain,
            "requires_external_verify": self.requires_external_verify,
            "requires_lawyer": self.requires_lawyer,
            "reasons": self.reasons,
        }


# ============================================================================
# L1. Intent & Risk Classifier
# ============================================================================

# 不可逆操作のマーカー（時効・権利放棄・署名など）→ requires_lawyer 強制
_IRREVERSIBLE_MARKERS = [
    "時効", "消滅時効", "除斥期間", "出訴期間", "提訴期限",
    "権利放棄", "放棄します", "取下げ", "取り下げ", "示談書", "和解契約",
    "署名", "押印", "サインし", "合意書", "誓約書", "клиент",  # noqa (typo-guard)
    "上訴期限", "控訴期限", "クーリングオフ期限", "クーリング・オフ",
]

# 緊急マーカー → venue=emergency
_EMERGENCY_MARKERS = [
    "殺", "死ぬ", "自殺", "今すぐ", "いますぐ", "助けて", "緊急",
    "暴力を受けて", "殴られ", "監禁", "連れ去", "110", "119", "命の危険",
]

# claim_type 推定キーワード
_PROCEDURAL_MARKERS = ["手続", "申立", "提出", "書式", "期限", "どこに", "必要書類", "流れ"]
_STRATEGIC_MARKERS = ["どうすれば", "どうしたら", "戦略", "勝て", "有利", "進め方", "次の一手", "べき"]
_OPINION_MARKERS = ["思いますか", "どう思う", "見解", "意見"]

# domain 推定キーワード（JapaneseLegalRAG.LegalDomain と整合）
_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "criminal": ["傷害", "暴行", "脅迫", "強要", "詐欺罪", "告訴", "被害届", "刑事"],
    "civil": ["損害賠償", "不法行為", "債務不履行", "契約", "民法", "慰謝料"],
    "labor": ["残業", "解雇", "賃金", "労災", "ハラスメント", "労働", "パワハラ", "未払い"],
    "consumer": ["返品", "クーリング", "消費者", "解約", "定期購入", "特定商取引"],
    "product_liability": ["欠陥", "製造物", "PL法", "リコール", "製品事故"],
    "family": ["離婚", "親権", "養育費", "面会交流", "DV", "婚姻"],
    "child_abuse": ["児童虐待", "子ども", "児相", "通告"],
    "elder_abuse": ["高齢者", "介護", "虐待", "後見"],
    "administrative": ["行政", "不服審査", "国家賠償", "許認可", "生活保護", "入管"],
    "stalking": ["ストーカー", "つきまとい", "盗撮", "リベンジポルノ"],
}


def classify_intent(question: str, llm_chat: Optional[LlmChat] = None) -> QueryIntent:
    """L1: ルールベースで意図・リスクを推定。

    設計書 §3.1 の Hard rules を構造で強制する:
      - irreversible → requires_lawyer = True（LM 単独回答禁止）
      - factual かつ risk>=med → requires_external_verify = True
    """
    q = question
    reasons: list[str] = []

    # --- domain ---
    domain = "general"
    best_hits = 0
    for dom, kws in _DOMAIN_KEYWORDS.items():
        hits = sum(1 for kw in kws if kw in q)
        if hits > best_hits:
            best_hits = hits
            domain = dom
    if best_hits:
        reasons.append(f"domain={domain}(kw×{best_hits})")

    # --- venue ---
    venue: Venue = "consult"
    if any(m in q for m in _EMERGENCY_MARKERS):
        venue = "emergency"
        reasons.append("emergency_marker")
    elif any(m in q for m in ["ADR", "あっせん", "仲裁", "調停"]):
        venue = "adr"
    elif any(m in q for m in ["訴訟", "提訴", "裁判", "訴え"]):
        venue = "litigation"

    # --- claim_type ---
    if any(m in q for m in _PROCEDURAL_MARKERS):
        claim_type: ClaimType = "procedural"
    elif any(m in q for m in _STRATEGIC_MARKERS):
        claim_type = "strategic"
    elif any(m in q for m in _OPINION_MARKERS):
        claim_type = "opinion"
    else:
        claim_type = "factual"
    reasons.append(f"claim_type={claim_type}")

    # --- risk_class ---
    irreversible = any(m in q for m in _IRREVERSIBLE_MARKERS)
    if irreversible:
        risk_class: RiskClass = "irreversible"
        reasons.append("irreversible_marker")
    elif venue in ("litigation", "emergency"):
        risk_class = "high"
    elif claim_type == "strategic":
        risk_class = "med"
    else:
        risk_class = "low"

    # --- Hard rules（設計書 §3.1）---
    requires_lawyer = risk_class == "irreversible"
    if requires_lawyer:
        reasons.append("HARD_RULE: irreversible→lawyer_required")

    requires_external_verify = claim_type == "factual" and risk_class in ("med", "high", "irreversible")
    if requires_external_verify:
        reasons.append("HARD_RULE: factual+risk≥med→external_verify")

    return QueryIntent(
        claim_type=claim_type,
        risk_class=risk_class,
        venue=venue,
        domain=domain,
        requires_external_verify=requires_external_verify,
        requires_lawyer=requires_lawyer,
        reasons=reasons,
    )


# ============================================================================
# L2. Mandatory Retrieval Gate
# ============================================================================

def retrieval_gate(
    question: str,
    *,
    retrieve_precedents: Optional[RetrieveFn],
    retrieve_statutes: Optional[RetrieveFn],
    top_k: int = 6,
) -> tuple[list[Source], list[str]]:
    """L2: 必須検索。判例 + 法令を取得し、id を連番付与。

    Returns (sources, warnings)。検索ゼロ件なら warning を立てる
    （L4 で「根拠なし→断定禁止」を強制するためのフラグ）。
    """
    warnings: list[str] = []
    sources: list[Source] = []

    def _collect(fn: Optional[RetrieveFn], kind: str, k: int) -> None:
        if fn is None:
            return
        try:
            got = fn(question, k)
        except Exception as e:  # 検索失敗は握りつぶさず warning として可視化
            warnings.append(f"retrieval_failed[{kind}]: {e}")
            logger.warning("retrieval_failed[%s]: %s", kind, e)
            return
        for s in got:
            s.kind = s.kind or kind
            sources.append(s)

    # 法令を先に（条文は根拠の土台）、次に判例
    _collect(retrieve_statutes, "statute", max(2, top_k // 2))
    _collect(retrieve_precedents, "precedent", top_k)

    # id 連番付与
    for i, s in enumerate(sources, 1):
        s.id = f"S{i}"

    if not sources:
        warnings.append("NO_SOURCES: 検索結果ゼロ件。LMは断定回答を禁止される。")

    return sources, warnings


# ============================================================================
# L4. Constrained Generation（source-tag / refusal-aware）
# ============================================================================

_REFUSAL_TOKEN = "INSUFFICIENT_EVIDENCE"

_SYSTEM_PROMPT_GROUNDED = """あなたは日本の法律実務に精通したアシスタントです。
**提示された根拠（法令・判例）のみ**を用いてユーザーの質問に答えてください。

絶対ルール（違反は重大な過失）:
1. 提示された根拠以外の知識で事実を断定しない。記憶や一般論で条文番号・判例・金額・期限を創作しない。
2. 主張の各文末に、依拠した根拠の ID を [S1] [S3] のように必ず付ける。
3. 提示根拠に該当が無い・薄い場合は、その点について必ず「提示された資料には根拠が見当たりません」と明示する。
4. 質問に答えるだけの根拠が全く無い場合は、本文の冒頭に %s とだけ書き、推測を述べない。
5. 結論 → 根拠（ID付き） → 注意点・不明点 の順で構造化。簡潔・実務的に。
6. 末尾に必ず「本回答は参考であり、具体的な法律行動は弁護士へ相談してください」を付記。
""" % _REFUSAL_TOKEN


def _build_context_blocks(sources: list[Source]) -> str:
    blocks = []
    for s in sources:
        label = s.citation or s.metadata.get("case_number") or s.metadata.get("title") or s.kind
        blocks.append(f"[{s.id}]（{s.kind}/{label}）\n{s.text[:1400]}")
    return "\n\n---\n\n".join(blocks)


def constrained_generate(
    question: str,
    sources: list[Source],
    intent: QueryIntent,
    llm_chat: LlmChat,
) -> str:
    """L4: source-tag を強制した生成。根拠ゼロなら refusal を促す。"""
    if not sources:
        # 構造的拒否：根拠が無いのに LM に自由生成させない
        return (
            f"{_REFUSAL_TOKEN}\n"
            "提示できる法令・判例データが見つかりませんでした。"
            "この質問には現時点で根拠ある回答ができません。"
            "弁護士・専門相談窓口への相談を推奨します。\n\n"
            "本回答は参考であり、具体的な法律行動は弁護士へ相談してください。"
        )
    context = _build_context_blocks(sources)
    user_prompt = (
        f"【質問】\n{question}\n\n"
        f"【利用可能な根拠（これ以外は使用禁止）】\n{context}\n\n"
        "上記根拠のみを用い、各主張に [S番号] を付して回答してください。"
    )
    return llm_chat(_SYSTEM_PROMPT_GROUNDED, user_prompt, 0.2)


# ============================================================================
# L5. Self-verification & Cross-check
# ============================================================================

# 事実主張に現れる検証対象パターン
_RE_SOURCE_TAG = re.compile(r"\[S(\d+)\]")
_RE_ARTICLE = re.compile(r"(?:民法|刑法|労働基準法|労働契約法|消費者契約法|特定商取引法|"
                         r"製造物責任法|行政手続法|行政事件訴訟法|児童虐待防止法|"
                         r"高齢者虐待防止法|ストーカー規制法|航空法|介護保険法)[第]?\s*"
                         r"(\d+)\s*条")
_RE_CASE = re.compile(r"(?:最判|最決|最大判|地判|高判|平成|令和|昭和)[^\s、。]*"
                      r"(?:\(受\)|\(あ\)|\(オ\)|\(ワ\)|号)")
_RE_MONEY = re.compile(r"(\d[\d,]*)\s*(?:万円|円|億円)")


@dataclass
class VerificationResult:
    ungrounded_claims: list[dict[str, Any]]
    cited_source_ids: list[str]
    refused: bool
    judge: Optional[dict[str, Any]]
    confidence: float

    def to_public(self) -> dict[str, Any]:
        return {
            "ungrounded_claims": self.ungrounded_claims,
            "cited_source_ids": self.cited_source_ids,
            "refused": self.refused,
            "judge": self.judge,
            "confidence": round(self.confidence, 3),
        }


def _extract_claims(answer: str) -> list[dict[str, Any]]:
    """L5: NER 簡易版。条文番号・判例・金額を主張として抽出。"""
    claims: list[dict[str, Any]] = []
    for m in _RE_ARTICLE.finditer(answer):
        claims.append({"type": "statute", "value": m.group(0)})
    for m in _RE_CASE.finditer(answer):
        claims.append({"type": "precedent", "value": m.group(0)})
    for m in _RE_MONEY.finditer(answer):
        claims.append({"type": "money", "value": m.group(0)})
    return claims


def _claim_grounded(claim_value: str, sources: list[Source]) -> bool:
    """主張の値（条文番号・金額の数字など）が根拠 text に現れるか。"""
    # 数字部分での緩い一致（条文番号・金額）
    nums = re.findall(r"\d+", claim_value)
    haystack = "\n".join(s.text for s in sources)
    if not nums:
        return claim_value in haystack
    return all(n in haystack for n in nums)


def self_verify(
    question: str,
    answer: str,
    sources: list[Source],
    *,
    judge_chat: Optional[LlmChat] = None,
) -> VerificationResult:
    """L5: 抽出した各 claim が retrieval 結果で裏付けられるか確認 + 独立 judge。"""
    refused = _REFUSAL_TOKEN in answer

    cited_ids = sorted({f"S{n}" for n in _RE_SOURCE_TAG.findall(answer)})
    valid_ids = {s.id for s in sources}
    # 存在しない ID を引用していたら ungrounded
    ungrounded: list[dict[str, Any]] = []
    for cid in cited_ids:
        if cid not in valid_ids:
            ungrounded.append({"type": "bad_source_id", "value": cid,
                               "note": "存在しない根拠IDを引用"})

    # 条文・判例・金額の裏付けチェック
    for claim in _extract_claims(answer):
        if not _claim_grounded(claim["value"], sources):
            ungrounded.append({**claim, "note": "根拠テキストに該当が見当たらない（UNGROUNDED）"})

    # source-tag が全く無い実質回答は減点
    no_tags = (not cited_ids) and (not refused) and len(answer) > 80

    # 独立 LLM judge（任意・別 model 推奨）
    judge_payload: Optional[dict[str, Any]] = None
    if judge_chat is not None and not refused and sources:
        try:
            judge_sys = (
                "あなたは法律回答の検証担当です。回答中の各事実主張が、"
                "提示された根拠だけで裏付けられているか判定してください。"
                "無裏付け・矛盾を JSON {\"verdict\":\"ok|revise\",\"unsupported\":[...]} で返答。"
            )
            ctx = _build_context_blocks(sources)
            judge_user = f"【根拠】\n{ctx}\n\n【検証対象の回答】\n{answer}"
            raw = judge_chat(judge_sys, judge_user, 0.1)
            judge_payload = _safe_json(raw) or {"verdict": "unparsed", "raw": raw[:500]}
        except Exception as e:
            judge_payload = {"verdict": "judge_error", "error": str(e)}

    # confidence 算出（設計書 §3.5 の reduce_confidence を簡略化）
    confidence = 1.0
    if refused:
        confidence = 0.0
    else:
        if not sources:
            confidence = 0.1
        confidence -= 0.3 * len(ungrounded)
        if no_tags:
            confidence -= 0.4
        if judge_payload and judge_payload.get("verdict") == "revise":
            confidence -= 0.3
        confidence = max(0.0, min(1.0, confidence))

    return VerificationResult(
        ungrounded_claims=ungrounded,
        cited_source_ids=[c for c in cited_ids if c in valid_ids],
        refused=refused,
        judge=judge_payload,
        confidence=confidence,
    )


def _safe_json(text: str) -> Optional[dict[str, Any]]:
    """LLM 出力から最初の JSON オブジェクトを抽出。"""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


# ============================================================================
# L7. Audit Log（SHA-256 chain）
# ============================================================================

def audit_log(payload: dict[str, Any], log_path: Path) -> dict[str, str]:
    """L7: query/response を SHA-256 chain で追記。改ざん検知可能にする。"""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    prev_hash = "0" * 64
    if log_path.exists():
        try:
            with log_path.open("r", encoding="utf-8") as f:
                last = None
                for line in f:
                    line = line.strip()
                    if line:
                        last = line
                if last:
                    prev_hash = json.loads(last).get("hash", prev_hash)
        except Exception as e:
            logger.warning("audit prev-hash read failed: %s", e)

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "prev_hash": prev_hash,
        "payload": payload,
    }
    body = json.dumps(record, ensure_ascii=False, sort_keys=True)
    cur_hash = hashlib.sha256((prev_hash + body).encode("utf-8")).hexdigest()
    record["hash"] = cur_hash
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"hash": cur_hash, "prev_hash": prev_hash}


# ============================================================================
# Orchestrator: L1 → L7
# ============================================================================

def run_harness(
    question: str,
    *,
    retrieve_precedents: Optional[RetrieveFn] = None,
    retrieve_statutes: Optional[RetrieveFn] = None,
    llm_chat: LlmChat,
    judge_chat: Optional[LlmChat] = None,
    top_k: int = 6,
    audit_path: Optional[Path] = None,
) -> dict[str, Any]:
    """全層を通した grounded 回答を返す。

    返り値は設計書 §3.4 の出力スキーマに準拠（透明性 payload を含む）。
    """
    t0 = time.time()

    # L1
    intent = classify_intent(question, llm_chat=None)

    # L2
    sources, warnings = retrieval_gate(
        question,
        retrieve_precedents=retrieve_precedents,
        retrieve_statutes=retrieve_statutes,
        top_k=top_k,
    )

    # L4
    answer = constrained_generate(question, sources, intent, llm_chat)

    # L5
    verification = self_verify(question, answer, sources, judge_chat=judge_chat)

    # L6 透明性 payload
    # 不可逆案件 / 低信頼度 / 幻覚（ungrounded）検出のいずれかで弁護士介入を促す
    lawyer_required = (
        intent.requires_lawyer
        or verification.confidence < 0.5
        or len(verification.ungrounded_claims) > 0
    )
    irreversible_warning = (
        "この質問は不可逆な判断（時効・権利放棄・署名等）に関わる可能性があります。"
        "実行前に必ず弁護士へ相談してください。"
        if intent.risk_class == "irreversible" else None
    )

    result: dict[str, Any] = {
        "answer": answer,
        "refused": verification.refused,
        "confidence": round(verification.confidence, 3),
        "risk_class": intent.risk_class,
        "lawyer_required": lawyer_required,
        "irreversible_action_warning": irreversible_warning,
        "intent": intent.to_public(),
        "sources": [s.to_public() for s in sources],
        "verification": verification.to_public(),
        "warnings": warnings,
        "harness_version": HARNESS_VERSION,
        "elapsed_ms": int((time.time() - t0) * 1000),
    }

    # L7
    if audit_path is not None:
        try:
            audit_meta = audit_log(
                {
                    "question": question,
                    "answer_excerpt": answer[:500],
                    "confidence": result["confidence"],
                    "source_ids": [s.id for s in sources],
                    "intent": intent.to_public(),
                },
                audit_path,
            )
            result["audit"] = audit_meta
        except Exception as e:
            result["audit"] = {"error": str(e)}

    return result
