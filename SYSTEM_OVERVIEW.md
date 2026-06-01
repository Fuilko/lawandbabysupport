# SYSTEM_OVERVIEW.md — 現有機能・資料夾構造・言語・DB・開発総流程・HARNESS

> コードベースの「今あるもの」を棚卸しした正準ドキュメント。
> 入口は `AGENTS.md`、主架構は `ARCHITECTURE.md`、環境/同期は `DEPLOYMENT_TOPOLOGY.md`、最新進捗は `PROGRESS.md`。
>
> 最終更新: **2026-06-02**

---

## 1. 使用言語（git 管理ファイル数）

| 言語/形式 | 数 | 用途 |
|---|---|---|
| Markdown (`.md`) | 124 | 設計書・docs・進捗 |
| **Python** (`.py`) | 116 | backend（RAG/harness/埋め込み）・crawlers・gis ingest |
| **Swift** (`.swift`) | 44 | iOS アプリ（SwiftUI + MLX + WhisperKit） |
| HTML (`.html`) | 37 | 紹介ページ・GIS フロント・Q-Map |
| CSV/Parquet | 15/13 | データセット・統計 |
| JSON | 9 | taxonomy 等スキーマ |
| SQL | 4 | PostGIS / judb スキーマ |
| YAML/YML | 5 | 設定・seed |
| JS / PS1 / sh | 2/3/2 | フロント・Windows/Mac スクリプト |

→ **二大言語 = Python（サーバ側）+ Swift（iOS）**。フロントは HTML/JS（軽量）。

---

## 2. 資料夾構造（トップレベル）

```
lawandbabysupport/
├── AGENTS.md / ARCHITECTURE.md / DEPLOYMENT_TOPOLOGY.md / PROGRESS.md / SYSTEM_OVERVIEW.md
├── DEPLOYMENT_GUIDE.md / RESUME_ON_NEW_MACHINE.md / README.md
├── ios/            ← iOS アプリ（Swift）
│   └── LegalShield/LegalShield/{Services, Views, Resources}
├── legalshield/    ← サーバ側コア（Python）
│   ├── backend/    （API・RAG・harness・埋め込み・分析）
│   ├── crawlers/   （法令・判例・統計・支援機関の収集）
│   ├── dispatch/   （tier_engine = 緊急度ルーティング）
│   ├── agents/ knowledge/ case_studies/ refs/ db/ frontend/ docs/
├── gis/            ← GIS サブシステム（Python + PostGIS + Leaflet）
│   └── {db, ingest, services, frontend, nginx}
├── data/           ← case_taxonomy（案件分類スキーマ）
├── aws/            ← bedrock_proxy（Lambda）
├── pocketmidwife/  ← 婦幼医療アプリ（姉妹プロダクト）
├── docs/           ← 設計書・判例RAGコーパス・助成金・PDF成果物
├── scripts/ tools/ shared/ tests/ private/ vendor/
```

---

## 3. 現有機能の分析

### 3-1. iOS アプリ（`ios/LegalShield/.../Services` 30+ / `Views` 7）

| カテゴリ | 主なモジュール | 機能 |
|---|---|---|
| **AI/LLM** | `LLMProvider` `LLMService` `LLMSettings` `MLXOnDeviceProvider` `OnDeviceSLMProvider` `CloudOllamaProvider` `AWSBedrockProvider` `MultiAgentOrchestrator` | プロバイダ抽象で on-device(MLX)/Ollama/Bedrock を切替。マルチエージェント協調 |
| **接地/RAG** | `JapaneseLegalRAG` `LegalHarnessService` `HarnessModels` | backend `/rag/answer`（L1-L7）呼出・出典付き回答 |
| **証拠保全** | `EvidenceManager` `CommunicationEvidenceImporter` `AuditLogService` `CaseReportGenerator` `ExportService` `PortableDBExporter` | SHA256+タイムスタンプ・監査ログ・通信証拠取込・案件レポート・可搬DB書出 |
| **音声** | `VoiceTriageService` `VoiceTriageSettings` `WhisperKitTranscriber` `InterviewCopilot` | 録音→文字起こし→トリアージ・問診補助 |
| **去識別化** | `LocationAnonymizer` `SecondaryVictimizationProtection` `ResearchDataManager` | GPS去識別・二次被害防止・差分プライバシー研究アップロード |
| **センサー** | `BLESensorManager` `MockSensorManager` `SensorProtocols` | BLE センサー（見守り）連携 |
| **案件/法務** | `CaseTaxonomyService` `AdministrativeLawModule` | 27カテゴリ分類・行政法モジュール |
| **連携/緊急** | `EmergencyEscalationService` `PartnerOrganizationModule` | tier別エスカレーション・NPO/専門家ルーティング |
| **画面** | `ContentView` `NewCaseSheet` `EvidenceCaptureView` `InterviewAssistView` `HarnessAnswerView` `SensorDashboardView` `AntiSurveillanceView` | 案件作成・証拠採取・問診・回答・センサー・反監視 |

### 3-2. サーバ backend（`legalshield/backend/` 27 モジュール）

| カテゴリ | モジュール | 機能 |
|---|---|---|
| **API/RAG** | `api` `rag_query` `rag_compare` `litigation_rag` `harness` | FastAPI・RAG検索・反幻覚ハーネス L1-L7 |
| **埋め込み/DB** | `elaws_embed*`(4) `unified_vectorize` `vectorize_all_datasets` `unified_db` | 法令・判例・各種データのベクトル化、統合DB |
| **分析** | `victim_assistant` `perpetrator_profiler` `jstage_analyzer` `trends` `heatmap` `muni_aggregate` `inspect_crime` | 被害者支援・加害者プロファイル・論文分析・統計・ヒートマップ・自治体集計 |
| **証拠/地理** | `evidence_vault` `geocode` `geocode_simple` `merge_facilities` | 証拠保管庫・ジオコーディング・施設統合 |
| **その他** | `anti_grafting` `poc_report` `full_ingest_windows` | 接ぎ木防止・PoCレポート・一括取込 |

### 3-3. crawlers（`legalshield/crawlers/`）
法令(e-Laws)・判例・e-Stat 犯罪統計・NPA・法テラス・弁護士会・NITE リコール・自治体条例・台湾司法 等を収集。

### 3-4. GIS（`gis/`）
PostGIS + ingest(DVセンター/犯罪統計/法テラス/N03行政界) + Leaflet フロント(Q-Map) + 公開 API(:8080)。

### 3-5. 姉妹プロダクト
`pocketmidwife/` — 婦幼医療補助（症状問診→Edge AI 検傷→Triage→救急紹介）。

---

## 4. 現有データベース

| DB | 種別 | 場所 | 内容 |
|---|---|---|---|
| **LanceDB + DuckDB** | ベクトルDB | backend（GPU機） | 国法 62.3万 + 判例 72.4万（ベクトル化済み） |
| **PostGIS** | 地理空間DB | `gis/`（Docker/EC2） | DVセンター・犯罪統計・法テラス・行政界。スキーマ `gis/db/00*.sql` |
| **judb** | RDB スキーマ | `legalshield/db/judb_schema.sql` | 司法データ構造 |
| **taxonomy_v1.json** | 分類スキーマ | `data/case_taxonomy/` | 27案件カテゴリ（iOS同梱・決定論的） |
| Parquet/CSV | データセット | 各所 | 統計・判例コーパス |
| 判例 RAG コーパス | JSONL/MD | `docs/research/precedents/` | 瑕疵担保/契約不適合/詐欺/PL/ドローン 等 |

---

## 5. 開発の総流程（主機 + APP）

### 5-1. サーバ（主機）開発フロー — Python / Windows RTX4080
```
① crawlers でデータ収集（法令・判例・統計）
      ↓
② elaws_embed* / unified_vectorize で埋め込み → LanceDB 構築
      ↓
③ backend/api.py（FastAPI）起動 → /rag/answer（harness L1-L7）を提供
      ↓
④ rag_query / rag_compare で検証（精度・出典）
      ↓
⑤（任意）小型SLM を LoRA 微調整 → GGUF → Ollama 配信
      ↓
⑥ Review 後 → AWS（Bedrock proxy / EC2+PostGIS）へ反映
```

### 5-2. iOS アプリ開発フロー — Swift / Mac (Xcode)
```
① Xcode でビルド（SPM: mlx-swift 0.25.x / mlx-swift-examples 2.25.x）
      ↓
② Services 実装（LLMProvider 抽象の背後で MLX/Ollama/Bedrock 切替）
      ↓
③ エッジ: WhisperKit 文字起こし → CaseTaxonomyService 分類 → LocationAnonymizer 去識別化
      ↓
④ LegalHarnessService → backend /rag/answer（出典付き回答）
      ↓
⑤ EvidenceManager で証拠保全（SHA256+監査）→ CaseReportGenerator 出力
      ↓
⑥ シミュレータ/実機で検証 → TestFlight → App Store
```

### 5-3. 接続点（APP ⇄ 主機）
APP は `LLMSettings.ollamaEndpoint`（既定 `http://100.76.218.124:8000`）でサーバに接続。
全UIは共通の **API コントラクト（/api/v1, /rag/*）** に従う（詳細 `DEPLOYMENT_TOPOLOGY.md` §7c）。

---

## 6. HARNESS（反幻覚の中核 — `legalshield/backend/harness.py`）

法律・医療の事実回答は**必ずこのハーネスを通す**。出典なき断定を構造的に禁止。

| 層 | 名称 | 役割 |
|---|---|---|
| **L1** | Intent & Risk Classifier | 意図・リスク分類。不可逆操作（時効/権利放棄/署名）は**弁護士強制** |
| **L2** | Mandatory Retrieval Gate | 必須検索。判例+法令を取得、**未取得なら生成禁止** |
| **L3** | Variable-loaded Reasoning | context-pack 装填（行政区域・予算・行動研究等の変数） |
| **L4** | Constrained Generation | source-tag 付き生成、refusal-aware（出典なきは「不明」） |
| **L5** | Self-verification & Cross-check | claim 抽出 → retrieval match → 独立 judge |
| **L6** | Transparency payload | source tag / confidence / risk badge / lawyer trigger |
| **L7** | Audit Log | SHA-256 chain で改竄検知 |

**縮退運転（Graceful Degradation）**: 検索失敗→断定拒否、judge失敗→回答は返す、クラウド全停止→エッジSLM継続、
最終防衛線として緊急ホットライン（110/189/#8008）は**どんな障害時も静的に必ず表示**。
設計全文: `docs/AGENT_SKILL_BOUND_DESIGN.md` / `docs/strategy/2026-05-31_edge_training_and_role_architecture.md`。

---

*コードを足したらこの棚卸しも更新すること。*
