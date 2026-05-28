# AGENT_SKILL_BOUND_DESIGN.md

> LegalShield / FEWN — 法律 AI agent の skill bound 設計書
> Version: 1.0
> Author: 劉 建志 (LIU CHIEN CHIH) + Cascade
> Date: 2026-05-28
> Status: Draft for review

---

## 0. 設計動機

本文書は、LegalShield と FEWN を支える法律 AI agent の **幻覚（hallucination）防止** および **能力境界（skill bound）自覚** の設計指針を定める。

直接的な開発契機は、2026-05-28 の対話セッションにおいて、Cascade agent 自身が以下の **4 種の失敗** を実演したことにある：

1. **Hallucination cascade** — 他 AI（Gemini）の戯劇化された記述を出典確認せずに踏襲
2. **Context illusion** — 本地資料庫が利用可能であるにもかかわらず再 retrieval を怠る
3. **Confirmation bias > Falsification** — 反証ステップを欠く一方向推論
4. **Narrative coherence > Factual precision** — 流暢な物語性を事実精度より優先

これらは **法律弱者を守る** という LegalShield の中核ミッションに対する致命的脅威である。本文書は、これらを **構造的・工学的** に防止するためのシステム設計を記述する。

---

## 1. 設計原則

### 1.1 ゼロ幻覚は不可能、可検証幻覚を目指す

工学上 100% の幻覚抑制は不可能。代わりに以下を目標とする：

- **検出可能性** — 幻覚が起きた場合、システムが自動的に検出する
- **不可避な可視性** — 未検証内容は UI 上で必ず可視化される
- **不可逆判断の阻止** — 重大判断の前に必ず弁護士介入が triggered される
- **追跡可能性** — エラー発生時にどの層で起きたか追跡できる

### 1.2 「知らない」を rewardable にする

LM の RLHF 段階で、「知らない」「確信がない」と回答することに **正の報酬** を与え、編造に強い負の報酬を与える。

### 1.3 構造的拘束 > Prompt 拘束

「ハルシネーションを起こさないでください」と prompt で頼むのは無効。代わりに **出力フォーマット・retrieval gate・cross-check** を構造で強制する。

### 1.4 ドメイン特性に応じた skill bound

法律ドメインは医療と並んで最も厳格な skill bound が必要：
- 不可逆な決定（時効、放棄、署名）が頻発
- 弱者・初学者が利用主体
- 誤導の社会コストが極めて高い

---

## 2. アーキテクチャ概要

```
┌──────────────────────────────────────────────────────┐
│  User Query                                          │
└──────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  L1. Intent & Risk Classifier                        │
│      - claim_type / risk_class / venue               │
│      - requires_external_verify / requires_lawyer    │
└──────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  L2. Mandatory Retrieval Gate                        │
│      - User upload RAG (highest priority)            │
│      - Internal KB RAG (laws, precedents, forms)     │
│      - External API (court, bar, MOJ)                │
│      - Cross-AI quarantine                           │
└──────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  L3. Variable-loaded Reasoning Engine                │
│      - Administrative topology                       │
│      - Budget / parliament cycle                     │
│      - Legal code layer                              │
│      - Behavioral economics models                   │
│      - Empirical priors / statistics                 │
│      - Social graph                                  │
└──────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  L4. Constrained Generation                          │
│      - Source-tagged generation                      │
│      - Refusal-aware decoding                        │
│      - Structured output schema (JSON)               │
└──────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  L5. Self-verification & Cross-check                 │
│      - Claim extractor                               │
│      - Retrieval match check                         │
│      - Independent LLM judge                         │
│      - Counterfactual / red-team step                │
└──────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  L6. Transparency UI                                 │
│      - Source tags inline                            │
│      - Confidence per claim                          │
│      - "Unverified" always visible                   │
│      - Risk-class badge                              │
│      - Lawyer-required trigger                       │
└──────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  L7. Audit Log + Feedback Loop                       │
│      - SHA-256 chained query/response log            │
│      - User correction → training data               │
│      - Outcome tracking                              │
└──────────────────────────────────────────────────────┘
```

---

## 3. 各層の詳細設計

### 3.1 Layer 1: Intent & Risk Classifier

```python
class QueryIntent:
    claim_type: Literal["factual", "strategic", "opinion", "procedural"]
    risk_class: Literal["low", "med", "high", "irreversible"]
    venue: Literal["consult", "adr", "litigation", "emergency"]
    requires_external_verify: bool
    requires_lawyer: bool
    domain: Literal["civil", "criminal", "labor", "family", ...]
```

**Hard rules:**
- `risk_class == "irreversible"` → `requires_lawyer = True`、LM 単独回答禁止
- `claim_type == "factual"` AND `risk_class >= "med"` → `requires_external_verify = True`

### 3.2 Layer 2: Mandatory Retrieval Gate

**Source priority order:**

| 優先 | Source | Trust |
|---|---|---|
| 1 | User upload (current case docs) | High |
| 2 | Official KB (laws, precedents, court forms) | High |
| 3 | Verified DB (judgement search, registry) | High |
| 4 | Government / bar association websites | Medium-High |
| 5 | Academic papers, peer-reviewed | Medium |
| 6 | Industry articles, lawyer blogs | Low |
| 7 | Other AI generated content | **Quarantined** |

**Cross-AI quarantine rule:**

User がアップロードした「他 AI（ChatGPT、Gemini、Claude 等）との対話ログ」は、LegalShield 内では `provenance: untrusted-ai` タグが自動付与される。Reasoning 素材としては利用可だが、**事実主張の根拠としては引用禁止**。

### 3.3 Layer 3: Variable-loaded Reasoning Engine

これは LegalShield のドメイン特化要素。各案件タイプごとに **変数群（context pack）** を pre-load する：

#### 3.3.1 Administrative Topology

```yaml
案件 type に応じて load:
  - 関連省庁・自治体・独立行政法人
  - 各機関の権限範囲
  - 行政分権の交差点
  
例（製品 PL 案件）:
  - 消費者庁（PL 法所管）
  - 経産省（NITE）
  - 国交省（運輸関連 product）
  - 厚労省（医療機器、食品）
  - 各業界所管省庁
```

#### 3.3.2 Budget / Parliament Cycle

```yaml
予算サイクル（補助金事業者紛争に重要）:
  4-6月: 新年度公募
  7-8月: 概算要求
  12月: 予算閣議決定
  1-3月: 国会審議
  3月末: 予算成立

案件への含意:
  - 補助金事業者の場合、紛争タイミングと審査タイミングの関係
  - 国会会期中は scandal 化リスク高
  - 概算要求期は政策温度の認識が起こりやすい
```

#### 3.3.3 Legal Code Layer

```yaml
案件 type ごとに mandatory citation:
  - 適用条文（条文番号 + 内容）
  - 代表的判例（最高裁・地裁主要例）
  - 学説の傾向
  - 実務の運用

例（契約不適合案件）:
  - 民法 415, 562-564, 566
  - 関連最判 (e.g., 平成XX年判例)
  - 商事・消費者契約特則
```

#### 3.3.4 Behavioral Economics Models

```yaml
当事者・関係者の意思決定モデル:
  - Loss aversion (Kahneman) — 損失重み 2-2.5x
  - Status quo bias
  - Sunk cost fallacy
  - Anchoring effect
  - Overconfidence bias
  - Endowment effect

組織別補正:
  - 大企業: bureaucratic risk aversion
  - 公務員: 「事前知って静観」恐怖
  - VC 出資者: 投資組合 reputation 重視
  - 個人事業主: cash flow 制約
```

#### 3.3.5 Empirical Priors

```yaml
統計データ:
  - 各 ADR 機関の和解成立率
  - 訴訟認容率（請求金 比率）
  - 平均期日数
  - 各種補助金の継続率/打切率
  - 各種紛争の媒体報道率
```

#### 3.3.6 Social Graph

```yaml
案件関係者のネットワーク:
  - 公的肩書 + 所属
  - 業界内ネットワーク
  - 学界・研究ネットワーク
  - 政策立案ネットワーク
  - 出資・取引関係
```

### 3.4 Layer 4: Constrained Generation

#### Output Schema (JSON)

```json
{
  "answer": "...",
  "facts_used": [
    {"claim": "...", "source": "doc#L123", "confidence": 0.95}
  ],
  "inferences": [
    {"reasoning": "...", "based_on": ["fact_1", "fact_2"], "confidence": 0.80}
  ],
  "unknown_areas": ["..."],
  "next_steps": [...],
  "lawyer_required": true,
  "irreversible_action_warning": null,
  "harness_version": "1.0",
  "variables_loaded": ["admin_topo", "legal_code", ...]
}
```

#### Refusal-aware Decoding

LM が「不確実」と判断した場合、`"I_DONT_KNOW"` token を出力する訓練を行う。RLHF で：
- 編造 → 強い負報酬
- 「知らない」と正確に回答 → 正報酬
- ユーザー訂正後の自己修正 → 正報酬

### 3.5 Layer 5: Self-verification

#### Claim Extractor

NER モデルで以下を抽出：
- 人名
- 機関名
- 法条文番号
- 金額・日付
- 判例番号

#### Retrieval Match Check

各 claim が L2 retrieval 結果に match するか確認：

```python
for claim in extracted_claims:
    if not any(claim_matches(claim, doc) for doc in retrieved_docs):
        flag(claim, "UNGROUNDED")
        reduce_confidence(claim, 0.3)
```

#### Independent LLM Judge

主応答 LM とは異なる model で二次審査：
```
Judge prompt:
"以下の回答中、各事実主張は提供された retrieval 結果で
裏付けられていますか？無裏付け or 矛盾を列挙してください。"
```

#### Counterfactual / Red-team Step

```
Red-team prompt:
"以下の回答が間違っている可能性のある主張 3 件を挙げ、
それぞれの反証検証方法を示してください。"
```

### 3.6 Layer 6: Transparency UI

UI には常に以下を表示：

```
[回答]
本文 ...

[根拠]
[1] ✓ 検証済 (user_upload://通知ログ.md L17)
[2] ✓ 検証済 (官公庁 https://...)
[3] ⚠ AI 推論 (要弁護士確認)
[4] ✗ 検証不能 — 推論ではあるが未確認

[信頼度] ●●●●○ 4/5
[リスク] 🟡 medium (戦略判断、不可逆ではない)
[弁護士相談] ⚠ 推奨 (最終決定は弁護士確認)

[Used variable groups]
✓ Administrative topology
✓ Legal code layer
✓ Behavioral economics
✗ Budget cycle (not loaded)
```

### 3.7 Layer 7: Audit Log

- 全 query/response を SHA-256 chain で永続化
- ユーザー訂正は negative training set に追加
- 案件結果（実 ADR/判決値）と AI 予測を対照、calibration 校正

---

## 4. 案件 type 別 pre-load 設計

各 type ごとに、必要な variable groups を事前定義：

| 案件 type | admin_topo | budget_cycle | legal_code | behavioral | empirical | social_graph |
|---|---|---|---|---|---|---|
| 契約紛争 (BtoB) | ○ | △ | ◎ | ◎ | ◎ | ○ |
| 契約紛争 (BtoC) | ◎ | × | ◎ | ◎ | ◎ | × |
| 補助金事業者紛争 | ◎ | ◎ | ◎ | ◎ | ◎ | ◎ |
| 労働紛争 | ◎ | × | ◎ | ◎ | ◎ | △ |
| 家事事件 | △ | × | ◎ | ◎ | ◎ | ○ |
| 製品事故・PL | ◎ | △ | ◎ | ◎ | ◎ | ○ |
| 行政訴訟 | ◎ | ◎ | ◎ | ◎ | ◎ | ○ |
| 国際商事 | ◎ | △ | ◎ | ◎ | △ | ◎ |

凡例: ◎ 必須 / ○ 推奨 / △ 任意 / × 不要

---

## 5. Pre-implementation 戦略

### 5.1 Variable group のテンプレート化

各 group をテンプレ化し、新案件登録時に：

1. **case type classifier** が type を判定
2. 対応する variable groups が自動 load
3. 必要に応じてユーザーに追加情報を求める
4. Variable pack が reasoning engine に注入される

### 5.2 ドメイン KB の構築

優先 KB:
1. **法令データベース** — e-Gov 法令検索 API
2. **判例データベース** — 裁判所判例検索 + 第二次商用 DB
3. **行政組織図** — 各省庁公開資料の構造化
4. **予算サイクル** — 各事業の公募・採択履歴
5. **行動経済学モデル** — 査読論文ベース
6. **業界統計** — 各 ADR 機関統計、各種紛争白書

### 5.3 案件知識のコールド・スタート問題

新案件タイプ初遭遇時の挙動：
- まず `domain: unknown` flag を立てる
- 弁護士介入を必須化
- 段階的に variable group を構築
- 案件完了後に knowledge base に統合

---

## 6. 既知の失敗事例集（Negative Training Set）

### Case 6.1: 2026-05-28 Mapry 案件分析対話

**失敗 1: Hallucination cascade**

ユーザーがアップロードした Gemini 対話ログから「大竹将之 = 殿堂級老牌律師」を引用、独自検証なし。

**実際**: 大竹将之氏は元検察官 15 年 + 外交官 + 2024 年弁護士登録の転身組（東京国際法律事務所）。Gemini の記述は事実無根。

**根本原因**:
- Cross-AI quarantine の不在
- L2 retrieval gate を skip

**対策**: provenance: untrusted-ai タグの強制付与、事実主張時の自動 web verify。

---

**失敗 2: Context illusion**

申立金額を「800 万」と認識。ユーザーから訂正。

**実際**: 6,800 万円（製品代金 800 + 損害賠償 6,000）— 既に通知ログ・勝率分析機密に明記。

**根本原因**:
- Read once, run on memory
- ユーザー意図確認の欠如

**対策**: Mandatory re-grep on key facts、案件メタ情報の専用 fact card。

---

**失敗 3: Persona 確認の欠如**

「律師から律師へ B1 通知」を提案。ユーザーは無代理人（本人申立て）。

**実際**: 通知ログ L19 に「本人申立（弁護士委任は別途検討中）」と明記済。

**根本原因**:
- 持続的 fact card の不在
- 一般化された助言の自動生成

**対策**: 案件冒頭で persona card を構築し、全 reasoning ステップに injection。

---

**失敗 4: Over-correction bias**

「FFPRI 山口先生は何もしない」と過度に主張、Gemini の「茶話施圧」描写を全否定。

**実際**: 山口浩和領域長には自己保護動機・FFPRI 機関責任・学術的興味・キャリアインセンティブ等、業界内での非公式情報共有を駆動する 60-80% の確率源あり。

**根本原因**:
- Behavioral economics model の不在
- 二項対立的判断（全肯定 or 全否定）
- Confirmation bias（前 turn 訂正への過剰補正）

**対策**: 確率分布での回答、変数群完備での再シミュレーション、red-team step 強制。

---

**失敗 5: Venue 区別の混同**

「強要罪未遂・業務妨害の紅線」を ADR 程序内主張にも適用。ユーザー指摘で訂正。

**実際**: ADR 程序内主張は「正当な権利行使」として不法行為成立せず（最判昭和 53.10.30 等）。

**根本原因**:
- Venue 区別 model の不在
- 「合法 vs 違法」二項判断（実務的纏訟成本を無視）

**対策**: Venue-tagged risk model 導入、纏訟成本 (process burden) を独立次元として評価。

---

**失敗 6: Skill bound の自己認識の欠如**

事実検証なしに具体的人物を語る。ユーザーが「網路找還是亂說」と問うまで自己訂正なし。

**根本原因**:
- Confidence 閾値の不在
- ユーザー反問が triggered されないと self-check しない

**対策**:
- 全人名・機関名で `confidence < 0.8` なら自動 web search trigger
- 周期的 self-audit step（"have I verified all factual claims?"）

---

## 7. 実装ロードマップ

### Phase 1 (2026 Q3-Q4): Core Harness
- [ ] Intent classifier 実装
- [ ] Retrieval gate hard rule 実装
- [ ] Cross-AI quarantine 実装
- [ ] Source-tagged output 実装

### Phase 2 (2027 Q1-Q2): Variable Engine
- [ ] Administrative topology DB 構築
- [ ] Legal code KB 構築
- [ ] Budget cycle data integration
- [ ] Behavioral econ model integration

### Phase 3 (2027 Q3-): Domain Expansion
- [ ] 案件 type 別 variable pack
- [ ] 案件結果 outcome tracking
- [ ] Calibration loop

### Phase 4 (2028-): SLM Optimization
- [ ] SLM 用の constrained generation
- [ ] Refusal head 訓練
- [ ] Edge deployment

---

## 8. ガバナンス

### 8.1 弁護士監修

- LegalShield の本番運用は弁護士監修必須
- 案件 type 別の最低限弁護士介入頻度を定める

### 8.2 ユーザー保護

- 不可逆判断の前は必ず弁護士相談 trigger
- 全 audit log は user に公開可能にする
- 訂正・苦情の即時反映機構

### 8.3 開発者規律

- Harness を bypass する prompt engineering は禁止
- 新機能は必ず L1-L7 を通過
- 月次の hallucination audit 実施

---

## 9. 改訂履歴

| Version | Date | 改訂内容 |
|---|---|---|
| 0.1 | 2026-05-28 | 初版骨格 |
| 1.0 | 2026-05-28 | 失敗事例 6 件を反映、変数群定義 |

---

> 本書は Mapry 案件 ADR 期日（2026-06-30）前後の対話実体験をもとに、LegalShield と FEWN の「人を守るための AI」設計の出発点として記述された。
