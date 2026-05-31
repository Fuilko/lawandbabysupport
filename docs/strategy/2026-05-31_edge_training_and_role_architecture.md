# エッジ訓練・5ロール利用アーキテクチャ・障害分離 設計書

**作成日**：2026-05-31
**対象**：劉 建志（Windows 機での作業範囲）
**前提**：Swift/iOS は Mac で開発。本機（Windows + RTX 4080）では「①小型モデル訓練」「②サーバ側アーキテクチャ」「③障害分離」を担当。

---

## 0. 実測した本機の能力（2026-05-31）

| 項目 | 状態 | 訓練への含意 |
|---|---|---|
| GPU | RTX 4080 / **16GB** VRAM | 3B の LoRA/QLoRA 微調整は十分可能。7B も QLoRA なら可 |
| `.venv` | torch 2.6.0+cu124・CUDA有効・transformers 5.8.0 | 推論・LoRA(fp16) の土台は完成 |
| 不足 | `peft` `trl` `datasets` `accelerate` `bitsandbytes` | 微調整前に install 必要 |
| WSL2 | Ubuntu(v2) 利用可 | QLoRA / Unsloth / bitsandbytes はこちらが安定 |
| Ollama | 起動中（:11434） | 訓練後 GGUF を `ollama create` で即配信可 |

---

## 1. 小型モデル訓練計画（エッジ・トリアージSLM）

### 1-1. 役割分担：大小2モデルの協調

ユーザーの構想（端末で問題整理 → 主DBへ送ってLLM分析）は、**2層モデル構成**で実現します。

```
┌─ 端末/エッジ（小型 3B SLM）──────────┐     ┌─ 主DB側（大型 27B LLM）────────────┐
│ 役割：トリアージ                       │     │ 役割：本格分析（grounded）          │
│ ・ユーザーの自由文を「分類＋構造化」   │ ──▶ │ ・/rag/answer（L1-L7 harness）      │
│ ・緊急度判定・カテゴリ確定             │ 構造化│ ・法令＋判例を検索して根拠付き回答  │
│ ・個人情報を除去した JSON だけ送信     │ JSON │ ・gemma3:27b 等                     │
│ ・オフラインでも動く                   │     │ ・出典・信頼度・弁護士フラグ付与     │
└────────────────────────────────────────┘     └─────────────────────────────────────┘
        Qwen2.5-3B / Gemma-2-2B                          gemma3:27b（既存）
        ↑ ここを訓練する                                  ↑ 訓練不要（プロンプト＋RAGで運用）
```

**重要**：今回作った `harness.py` の L1（Intent & Risk Classifier）は **ルールベースで既に動いています**。小型モデルの訓練は「自由文の理解精度を上げる」拡張であり、**必須ではなく改善**です。まずプロンプトの3B（zero/few-shot）で運用開始し、データが貯まってから微調整するのが最短ROI。

### 1-2. 訓練対象モデルの選定

| モデル | サイズ | 16GBでの訓練 | 日本語 | 推奨用途 |
|---|---|---|---|---|
| **Qwen2.5-3B-Instruct** | 3B | ◎ fp16 LoRA / QLoRA | ◎ | **第一候補**（多言語・軽量・ライセンス可） |
| Gemma-2-2B-jpn-it | 2B | ◎ 最も軽い | ◎日本語特化 | 端末最軽量を狙うなら |
| Phi-3.5-mini | 3.8B | ○ QLoRA | △ | 推論力重視 |

### 1-3. 訓練の3段階（段階的に着手）

```
Phase A: データ無し → プロンプト運用（今すぐ）
   Ollama に qwen2.5:3b を pull → harness の triage 役として few-shot で使う
   （訓練不要。即日でエッジ分類が動く）

Phase B: 弱ラベル訓練（データが数百件貯まったら）
   材料：taxonomy_v1.json（27カテゴリ）＋ seed_queries.yaml ＋ intake_session ログ
   → 「自由文 → {category, urgency, domain}」の JSONL を生成
   → LoRA 微調整（fp16, .venv で peft+trl）
   → 分類精度をルールベースと比較（eval set）

Phase C: 蒸留・本番化（精度確認後）
   LoRA をマージ → GGUF 変換 → ollama create → エッジ配信
   端末（Mac/iOS）へは MLX/CoreML 変換（Mac 側作業）
```

### 1-4. 本機で「今すぐできる」こと

```powershell
# 1) エッジ用 3B を Ollama に入れて triage を即運用（訓練不要）
ollama pull qwen2.5:3b

# 2) 後で微調整するなら .venv に訓練ライブラリを追加（要確認）
#    ※ ネイティブWindowsは fp16 LoRA。QLoRA(4bit)はWSL2推奨。
& "d:\projects\LegalShield\.venv\Scripts\pip.exe" install peft trl datasets accelerate
```

> ⚠️ `bitsandbytes`（QLoRA 4bit）はネイティブWindowsで不安定。QLoRAは WSL2 Ubuntu で行うこと。fp16 LoRA なら 16GB + .venv のままで Qwen2.5-3B が回ります。

### 1-5. データパイプライン（訓練データの作り方）

```
[材料]                          [変換]                    [出力]
taxonomy_v1.json (27カテゴリ) ┐
seed_queries.yaml (種文)      ├─▶ build_triage_dataset.py ─▶ triage_train.jsonl
intake_session ログ(匿名)     ┘   （自由文→ラベルの対）        {messages:[...], label:{category,urgency,domain}}
judb/litigation DuckDB        ──▶ （判例はRAG用、訓練ラベルではない）
```

JSONL 1 行の形（instruction-tuning 形式）:
```json
{"messages":[
  {"role":"system","content":"あなたは法律相談のトリアージAI。カテゴリ・緊急度・分野をJSONで返す。"},
  {"role":"user","content":"上司から毎日侮辱され、残業代も払われない"},
  {"role":"assistant","content":"{\"category\":\"workplace_harassment\",\"urgency\":\"high\",\"domain\":\"labor\"}"}
]}
```

---

## 2. 5ロール利用アーキテクチャ＋情報フロー

### 2-1. 5つのロールと権限・見える情報

| ロール | 誰 | 端末/画面 | 見える情報 | 見えない情報 |
|---|---|---|---|---|
| **使用者** (User) | 被害当事者 | iOSアプリ（エッジ） | 自分の相談・回答・出典・自分の証拠 | 他人の一切 |
| **導入者** (Introducer) | 自治体・NPO・支援センター | 地域ダッシュボード | 地域の**集計のみ**（k≥5）・リスクマップ | 個人特定情報・生データ |
| **協力者** (Collaborator) | CALL4・弁護団・公証人 | 連携API/公証人サーバ | FEWN暗号マッチ結果・**本人同意済み**案件サマリ | 顔・電話・住所（Vault内、2-of-N同意要） |
| **管理者** (Admin) | 運用責任者 | 管理ダッシュボード | 監査ログ・稼働状況・**仮名**統計・RBAC管理 | 生PII（復元には2-of-N決議） |
| **開発者** (Developer) | 劉（あなた） | コード/CI/CD | 全コード・スキーマ・**テストデータのみ** | 本番のVault実データ（Review→AWS反映） |

### 2-2. 情報ストリーム（端末→主DB→各ロール）

既存の `DATA_FLOW_PSEUDONYMIZATION.md`（Vault + Operating DB の2層分離）と完全整合させます。

```
┌─ 使用者（端末・エッジ）────────────────────────────────┐
│ ① 自由文/音声 → エッジ3B SLM がトリアージ              │
│ ② 生データは端末内 AES-GCM 暗号化（Secure Enclave）    │
│ ③ 送信は「分離」：トークン + 去識別化 triage JSON だけ │
└───────────────┬────────────────────────────────────────┘
                │ HTTPS (mTLS)
                ▼
        ┌───────────────────────────────────────┐
        │ 主DB側 = 2つに物理分離                  │
        │                                         │
        │ ① IDENTIFIER VAULT (HSM/KMS, 別VPC)     │  ← 管理者も直接見れない
        │    user_token→実UUID / 顔 / 電話        │     復元= 2-of-N + 本人同意
        │                                         │
        │ ② OPERATING DB (公開・連携・分析)        │  ← ここから各ロールへ配信
        │    event_id / location_hex(500m) /      │
        │    time_window(1h) / category / urgency │
        │    + /rag/answer (L1-L7 grounded LLM)    │
        └───────┬─────────┬──────────┬────────────┘
                │         │          │
     導入者 ◀──┤         │          ├──▶ 協力者(CALL4)
     k≥5集計    │         │          │     FEWN暗号マッチ
     リスクMap  │         │          │     +本人同意済サマリ
                ▼         ▼
            管理者      開発者
          監査/RBAC   テストデータのみ
                      Review後→AWS
```

### 2-3. 同意ラダー T0〜T4 との対応

情報がどのロールまで流れるかは、ユーザーの同意段階で決まります（AGENT_HANDOFF.md の5段階ラダー）。

| 段階 | 情報の到達範囲 |
|---|---|
| T0 端末完結 | 使用者のみ（送信なし、エッジSLMだけ） |
| T1 統計化 | + 導入者（location_hex+time_windowの集計、k≥5） |
| T2 個人化助言 | + 主DB `/rag/answer`（仮名のまま grounded 回答） |
| T3 詳細記録 | + 管理者（仮名・監査）、FEWN暗号マッチ参加 |
| T4 第三者共有 | + 協力者（CALL4弁護団へ、2-of-N＋本人同意で実名開示） |

### 2-4. 開発者→本番の流れ（あなたの運用ルール）

ユーザー要望「AWSは私のReview後に上げる」を制度化：

```
ローカル開発 (Windows/.venv + Mac/Xcode)
   │ git push（feature ブランチ）
   ▼
CALL4/協力者が local repo で同期開発（PR を出す）
   │ Pull Request
   ▼
★ 開発者(劉) が Review ★  ← ここが必須ゲート
   │ approve + merge to main
   ▼
GitHub Actions → AWS デプロイ（main のみ）
```

協力モデルは「**協力者は local repo + PR まで。本番AWS反映は劉のReview後のみ**」が最速かつ安全。
（git 同期手順書は別途 `docs/setup/COLLABORATOR_ONBOARDING.md` を作成可能）

---

## 3. 障害分離設計（小バグで全体が死なない）

### 3-1. 基本原則：Graceful Degradation（縮退運転）

> **「一部が壊れても、ユーザーには必ず何かを返す。完璧な回答 < 落ちないこと」**

これは AGENT_HANDOFF.md の design philosophy にも明記済みの既定方針。今回の `harness.py` も既にこの思想で実装済み：

| 壊れた箇所 | 従来なら | 本実装の縮退動作 |
|---|---|---|
| 検索（LanceDB）失敗 | 例外で停止 | warning を立て、根拠ゼロ→**LLMに断定させず拒否** |
| 独立judge LLM失敗 | 全体エラー | `judge_error` を記録し**回答自体は返す** |
| 監査ログ書込失敗 | データ不整合 | `audit.error` を付けて**回答は返す** |
| クラウドLLM全停止 | 無応答 | iOS が**生LLMフォールバック**＋「未検証」明示 |
| 主DB全停止 | アプリ死亡 | 端末エッジSLMで**最低限のトリアージ継続** |

### 3-2. アーキテクチャ層での分離（独立した壊れ方）

```
[完全独立した2バックエンド]（既存方針・メモリ参照）
  ・legalshield/backend  … 私有GPU・重い・Ollama       ← 落ちても↓は生存
  ・gis/services/...      … 公開Docker・軽量・無LLM      ← 落ちても↑は生存

[サービス境界]
  Vault ⟂ Operating DB（別VPC/別RDS）  … 片方侵害でも他方無事
  エッジ ⟂ クラウド                     … ネット断でもエッジ生存
```

### 3-3. 実装パターン（適用すべき技術）

| パターン | 目的 | 適用箇所 |
|---|---|---|
| **Timeout + Retry** | 1つの遅延が全体を巻き込まない | 全LLM/DB呼出（harnessは180s timeout済） |
| **Circuit Breaker** | 落ちてる依存を叩き続けない | Ollama/judge への呼出 |
| **Bulkhead（隔壁）** | あるカテゴリの過負荷が他に波及しない | category別のワーカー分離 |
| **Fallback chain** | 段階的縮退 | grounded → 生LLM → ルールベース → 静的FAQ |
| **Health check + 自動再起動** | 部分復旧 | docker compose healthcheck（gis 側に既存） |
| **try/except per-layer** | 1層の例外が全層を殺さない | harness は L2/L5/L7 で局所catch済 |

### 3-4. フォールバックチェーン（回答の縮退順序）

```
① /rag/answer（grounded・出典付き）         ← 通常
   ↓ 失敗
② 生LLM（/api/generate）＋「未検証」警告      ← クラウド生存時
   ↓ 失敗
③ 端末エッジ3B（オフライン分類のみ）         ← ネット断
   ↓ 失敗
④ 静的FAQ＋緊急ホットライン番号（常時表示）   ← 最終防衛線（必ず出す）
```

緊急ホットライン番号（110/189/#8008 等）は**どんな障害時も必ず表示**される静的UIに置く（DBにもLLMにも依存させない）。

---

## 4. このマシンでの「次の一手」候補

| 優先 | タスク | コマンド/成果物 | 所要 |
|---|---|---|---|
| すぐ | エッジ3Bをプロンプト運用 | `ollama pull qwen2.5:3b` | 5分 |
| 小 | 訓練ライブラリ導入 | `.venv` に `peft trl datasets accelerate` | 10分 |
| 中 | トリアージ訓練データ生成 | `build_triage_dataset.py`（taxonomy+seed→JSONL） | 半日 |
| 中 | LoRA微調整 → GGUF → Ollama | `train_triage_lora.py` | 数時間（GPU） |
| 中 | `/rag/answer` 本番ライブ検証 | `.venv` で uvicorn 起動 + 実クエリ | 30分 |
| 大 | 管理者ダッシュボード（節点8） | gis 側 Web UI + RBAC | 別セッション |

---

## 5. 一言まとめ

- **訓練**：4080(16GB)でQwenかGemmaの3BをLoRA微調整可能。ただし急がず、まずプロンプト運用→データ蓄積→微調整の順が最短。
- **5ロール**：端末で去識別化 → Vault/Operating の2層 → 同意段階(T0-T4)で各ロールへ情報が段階的に流れる。開発者(あなた)のReviewが本番反映の必須ゲート。
- **障害分離**：縮退運転を全層で徹底。`harness.py` は既にこの思想で実装済み。緊急番号だけは何があっても必ず表示。
