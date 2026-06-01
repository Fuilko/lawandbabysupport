# ARCHITECTURE.md — システム主架構（唯一の真実 / Single Source of Truth）

> 本書はシステム全体の正準アーキテクチャ記述。架構を変更したら**同一コミットで本書を更新**すること。
> 入口は `AGENTS.md`。最新の時系列進捗は `PROGRESS.md`。
>
> 最終更新: **2026-06-02**

---

## 1. 全体像

```
                ┌────────────────────────────────────────────┐
                │                iOS App (ios/)                │
                │  SwiftUI + on-device SLM(MLX) + WhisperKit   │
                │  証拠保全 / 録音トリアージ / 去識別化         │
                └───────────────┬───────────────┬──────────────┘
                                │ (private/重い)  │ (public/軽量)
                                ▼                ▼
        ┌──────────────────────────────┐  ┌──────────────────────────────┐
        │  legalshield/backend          │  │  gis/services/legalshield-api │
        │  FastAPI :8000 (Tailscale)    │  │  FastAPI :8080 (Docker)       │
        │  100.76.218.124               │  │  公開・無 LLM                 │
        │  - Ollama (gemma3:27b)        │  │  - PostGIS                    │
        │  - RAG over LanceDB           │  │  - nearest-support / tiles    │
        │  - harness.py (L1-L7)         │  │  - risk-score / region-stats  │
        │  - sentence-transformers/CUDA │  │                               │
        └───────────────┬──────────────┘  └───────────────┬──────────────┘
                        ▼                                  ▼
            ┌───────────────────────┐          ┌───────────────────────┐
            │ LanceDB + DuckDB       │          │ PostGIS                │
            │ 国法 623,000 件        │          │ DV センター / 犯罪統計 │
            │ 判例 724,443 件        │          │ 法テラス / 行政界(N03) │
            │ (vectorized)           │          │                        │
            └───────────────────────┘          └───────────────────────┘
```

**設計思想**: 重い/私有/GPU 依存（LLM・ベクトル検索）は `legalshield/backend`。
公開/軽量/LLM 不要（地図・最寄り支援・統計）は `gis/`。iOS は両者を使い分ける。

---

## 2. iOS アプリ（`ios/LegalShield/`）

- **UI**: SwiftUI（`Views/`）
- **オンデバイス LLM**: MLX（`MLXOnDeviceProvider`）— `mlx-swift 0.25.x` + `mlx-swift-examples 2.25.x`
- **音声認識**: WhisperKit（`WhisperKitTranscriber`）— `whisper-base` / `large-v3-turbo`
- **プロバイダ抽象**: `LLMProvider` プロトコル（背後に MLX / Ollama / Bedrock を差替可能）
- **去識別化**: `LocationAnonymizer`（hex / 仮想都市 / オフセット）
- **証拠保全**: `EvidenceManager`（SHA256 + タイムスタンプ + Audit Log）
- **NPO 紹介**: `PartnerOrganizationModule`（管轄・営業時間で routing）
- **緊急エスカレーション**: `EmergencyEscalationService`（tier 別、弁護士 trigger）
- **反幻覚クライアント**: `LegalHarnessService` → backend `/rag/answer`

### iOS ビルド注意（重要・端末間で再現必要）
- `project.pbxproj` と `Package.resolved` は **gitignore 対象**。別端末では SPM 解決と
  ファイル登録が必要になる場合がある。
- **依存ピン**: `mlx-swift` = `upToNextMajor 0.25.4`、`mlx-swift-examples` = `upToNextMajor 2.25.4`。
  古い `0.18.1` は Xcode 26 / iOS 26.5 SDK で C++ がコンパイル不可。
- **deployment target**: iOS 17.0 以上（MLX 要件）。
- 詳細手順・既知の落とし穴は `PROGRESS.md` の 2026-06-01 エントリ参照。

---

## 3. backend（`legalshield/backend/` — FastAPI :8000）

GPU 開発機（Windows, Tailscale `100.76.218.124`）上で稼働。

### 主要エンドポイント
```
GET  /health                  — Ollama / embed モデル状態
POST /rag/query               — 質問 → 埋め込み → LanceDB 検索 → Ollama 生成
POST /rag/retrieve            — 検索のみ（生成なし）
POST /rag/statutes            — 法令検索
POST /rag/partners            — 支援機関検索
POST /rag/answer              — ★ harness L1-L7 接地回答（推奨・iOS はこれを使う）
POST /api/generate /api/chat  — Ollama proxy（raw・事実回答に直接使わない）
```

### スタック
- **LLM**: Ollama `gemma3:27b`
- **埋め込み**: sentence-transformers（`query: ` プレフィックス, normalize）, CUDA
- **ベクトル DB**: LanceDB + DuckDB（判例 + 法令）
- **反幻覚**: `harness.py`（L1-L7、§5 参照）

### 主要モジュール
- `harness.py` — 反幻覚ハーネス（中核）
- `litigation_rag.py` / `rag_query.py` — RAG 検索
- `elaws_embed*.py` / `unified_vectorize.py` — 法令・データ埋め込み
- `victim_assistant.py` / `perpetrator_profiler.py` — 被害者支援 / 加害者プロファイル
- `evidence_vault.py` — 証拠保管（仮名化アーキ）
- `heatmap.py` / `trends.py` — 統計・可視化

---

## 4. GIS サブシステム（`gis/` — FastAPI :8080, Docker, 公開）

LLM 不要・公開データのみ・軽量。

### エンドポイント
```
GET  /api/v1/legalshield/nearest-support          — 最寄り支援機関
GET  /api/v1/legalshield/risk-score               — 地域リスクスコア
POST /api/v1/legalshield/incident-report          — 去識別化インシデント登録
GET  /api/v1/legalshield/region-stats/{pref_code} — 行政区域統計
GET  /api/v1/legalshield/tiles/{z}/{x}/{y}.pbf    — ベクタータイル
```

### 構成
- **DB**: PostGIS（`gis/db/*.sql`）
- **ETL**: `gis/ingest/`（DV センター・e-Stat 犯罪統計・法テラス・N03 行政界）
- **フロント**: Leaflet MVP（`gis/frontend/`, Q-Map prototype）
- **配備**: `gis/docker-compose.local.yml`, `gis/DEPLOYMENT.md`

---

## 5. 反幻覚ハーネス L1〜L7（`legalshield/backend/harness.py`）

法律・医療の事実回答は**必ず本ハーネスを通す**（`AGENTS.md` §2 と一体）。

| 層 | 名称 | 役割 |
|---|---|---|
| L1 | Intent & Risk Classifier | 意図・リスク分類。不可逆操作（時効・権利放棄・署名）は弁護士強制 |
| L2 | Mandatory Retrieval Gate | 必須検索。判例+法令を取得、**未取得なら生成禁止** |
| L3 | Variable-loaded Reasoning | context-pack 装填（行政区域・予算・行動研究等の変数） |
| L4 | Constrained Generation | source-tag 付き生成、refusal-aware（出典なきは「不明」） |
| L5 | Self-verification | claim 抽出 → retrieval match → 独立 judge |
| L6 | Transparency payload | source tag / confidence / risk badge / lawyer trigger |
| L7 | Audit Log | SHA-256 chain で改竄検知 |

設計指針の全文は `docs/AGENT_SKILL_BOUND_DESIGN.md`。

---

## 6. データベース / 知識源（接地の根拠）

| 種別 | 場所 | 用途 |
|---|---|---|
| 法令ベクトル | LanceDB（backend） | 国法 623,000 件 |
| 判例ベクトル | LanceDB（backend） | 判例 724,443 件 |
| 判例 RAG コーパス | `docs/research/precedents/*.jsonl` | 瑕疵担保 / 契約不適合 / 詐欺 / PL / ドローン 等 |
| 案件分類 | `data/case_taxonomy/taxonomy_v1.json` | 決定論的カテゴリ（iOS 同梱） |
| GIS 公開データ | PostGIS（`gis/`） | DV センター / 犯罪統計 / 法テラス / 行政界 |

---

## 7. プライバシー / 去識別化フロー

```
端末で採取（写真+SHA256 / 録音→文字起こし / GPS）
   │  ① LocationAnonymizer で GPS 去識別化（hex / 仮想都市 / オフセット）
   │  ② （計画）テキスト PII マスク（氏名・住所・電話）
   ▼
去識別化済みデータのみ送信
   │  ③ 研究/GIS アップロードは差分プライバシー(Laplace) + 暗号化
   ▼
backend / gis（生データは保持しない）
```

---

## 8. 既知の未完了領域（→ 詳細と時程は `PROGRESS.md`）

- iOS hexIndex が自前 schema（H3 非互換）→ 標準 H3 へ移行予定
- iOS 側 `AnonymizedLocation` / `HexAggregate` の GIS アップロード配線が未接続
- テキスト PII（自由文・文字起こし）の NER 去識別化が未実装
- 音声認識の**ファインチューニング**（ドメイン適応）が未実装（現状は推論のみ）
- `*.legalshield.jp` 本番エンドポイントは未デプロイ（AWS 構築待ち）

---

*この架構図と実装が乖離していると気づいたら、修正して本書を更新すること。*
