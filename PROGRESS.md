# PROGRESS.md — 開発進捗ログ（追記式・最新が上）

> **運用ルール**: 作業を終えたら、このファイルの最上部（日付見出しの直後）に新エントリを追記する。
> 書式: 日付 / 担当 / 何を・なぜ・影響範囲・次の一手。
> 入口は `AGENTS.md`、架構は `ARCHITECTURE.md`。**過去のチャット記憶より本ファイルを正とする。**

---

## 2026-06-09 (3) — 接地原則 §2.5 「利用者証拠優先原則」 + evidence_gate 導入（劉 + Devin）

**何を**:
- AGENTS.md §2.5 新原則「**利用者証拠優先原則**」を追加
- `legalshield/backend/evidence_gate.py` (312 行) 新規実装
  - `index_evidence_folder()` — 証拠フォルダ再帰列挙 + SHA256 + PDF text 抽出可否判定 (text vs scan)
  - `EvidenceManifest` — 案件単位の証拠台帳
  - `mark_read()` — agent が読了したファイルを記録
  - `assert_ready_for_analysis()` — coverage < min_coverage または OCR/vision pending あれば `EvidenceGateError` を raise
  - `coverage_banner()` — 分析報告先頭に挿入する透明性 metric

**なぜ**:
- 2026-06-09 mapry 案で重大な接地失敗が発生
- 53 件の証拠資料のうち実際に読んでいたのは 9 件 (17%)
- 残り 44 件には mapry 弁護士回信 1.6MB scan PDF、委任書、最終要求書、7 件の脅迫メール原文、18 件の証拠写真等が含まれていた
- 既存ファイルの要約だけで「全面分析」を生成 → 訴訟当事者構造を含めて根本的に誤った報告書を作成
- harness.py L1-L7 は法律 DB retrieval を必須化するが、**利用者証拠についての強制ゲートがなかった**
- 個別 agent の注意力に頼らず、構造的に防ぐ仕組みが必要

**影響範囲**:
- backend code: `legalshield/backend/evidence_gate.py`（新規）
- 規範 doc: `AGENTS.md` §2.5（新規）
- 運用変更: 案件分析前に必ず `evidence_manifest.json` を作り、coverage >= 90% かつ OCR/vision pending = 0 にすることが必須

**次の一手**:
- harness.run_harness() に optional な evidence_gate.assert_ready_for_analysis() フックを追加（次セッション）
- OCR pipeline 整備（tesseract or paddleocr 自動化、scan PDF を text に）
- vision pipeline 整備（read tool or 専用 vision model で証拠写真を読む）
- 既存 mapry 案について coverage 90% 達成（25 件 OCR + 21 件 vision を実行）

---

## 2026-06-09 (2) — 法令本物 ingest 完了：634,567 chunks / 8,732 法令（劉 + Devin）

**何を**:
1. **e-LAWS 全件ダウンロード**: `data_set/law/list.json` (8,790 件) を元に e-Gov API v1 から全法令の XML を取得。
2. **災害級失敗と修正**:
   - 初回 (workers=8, sleep=1s) は **e-Gov のレート制限を踏み**、HTTP 200 + HTML 「ご利用のページが見つかりません」を 8,640/8,785 (98.4%) で受信。
   - 旧スクリプトは `len(body) > 500` のみで判定、HTML 404 (33KB) を全て「成功」として保存。
   - LanceDB に 363,541 chunks ingest したが ~95% は HTML/CSS の網站樣板、retrieval が完全に汚染。
   - **修正**: `_is_real_xml()` で `<?xml` 開頭を必須化、 workers=3 sleep=2s に降速、HTML 受信時は exponential backoff retry。
   - 再ダウンロード: 8,775 ok / 15 真 404 / 0 rate-limit / 0 fail（193 分）。
3. **Ingest VRAM 修正**: 旧コードは sentence-transformers の中間 activation を解放せず、VRAM が 1.6→15.8GB まで累積し速度が 700→32 chunks/s に劣化。
   - `torch.inference_mode()` + sub-batch + `torch.cuda.empty_cache()` で VRAM を 1.6GB に固定。
   - 結果: **641,433 chunks / 19.6 分 / 547 chunks/s 安定**（旧の 17 倍速）。
4. **fallback ゴミ清掃**:
   - `extract_law_text()` の XML parse 失敗時 fallback path が、添付画像 base64 を含む全 XML を「all 条」として ingest していた（83,999 chunks / 847 法令、全て「身分證明證票規則」「服制」「自動車道標識様式」等の図式法令）。
   - **核心法律（民法/刑法/憲法/労働基準法/会社法/商法/消費者契約法/製造物責任法/DV防止法/ストーカー規制法）は 100% 純粋（bad=0）を確認**してから DELETE。
   - 加えて空殻 chunks（length<10、「。」「省略」等）6,866 件を DELETE。
5. **AGENTS.md 数値の真相確定**:
   - 旧記載「法令 **623,000 件**」は **chunk 数の意味**（法令件数なら 8,790）であることが確定。
   - 実体: **634,567 chunks / 8,732 unique laws / 2,556 MB**（pgvector HNSW 含む）。

**最終データベース状態**（pgvector port 5435）:
| Table | Rows | Unique laws | Size |
|---|---|---|---|
| precedents | 724,443 | — | 1,309 MB |
| **statutes (real e-LAWS)** | **634,567** | **8,732** | **2,556 MB** |
| litigation | 3,837 | — | 7 MB |
| **合計** | **1,362,847** chunks | | ~3.9 GB |

**E2E retrieval 検証結果**（HNSW 索引使用、~50-500ms）:
| Query | Top-1 結果 | 評価 |
|---|---|---|
| 製造物責任法 欠陥 | 製造物責任法 第2条「『欠陥』とは、当該製造物の特性…」 | ★ 教科書級 |
| 労働基準法 残業 三六協定 | 労働基準法 第36条 | ★ 完璧 |
| 消費者契約法 クーリングオフ | 消費者契約法 第12条、割賦販売法施行規則 | ○ 関連 |
| 刑法 詐欺罪 構成要件 | 組織犯罪処罰法 第3/13条 | △ 詐欺関連刑罰だが刑法246条直撃ではない |
| 民法 不法行為 損害賠償 | 民法施行法 第74条等 | △ 民法709条直撃ではないが汚染なし |
| DV防止法 保護命令 | （改善余地あり、要 hybrid BM25 検討） | △ |

**何が成功か**:
- **接地データの真実性**: 634,567 chunks は **真法令本文**（XML parse 成功 + base64 ゴミ排除済み）。
- **harness L2 が機能する基盤**: precedents + statutes 両方検索可能、cosine `<=>` HNSW、~50ms response。
- **AGENTS.md の宣称（623k）が実証された**: 634,567 ≈ 623,000 で誤差 1.8%。これで初めて「内容のある grounding DB」が完成。

**残課題**:
- core 法律（民法/刑法等）への retrieval が他の周辺法令に負けることがある → hybrid BM25 + dense or query rewrite を検討。
- iOS `LegalHarnessService` を /rag/answer に接続して E2E 完結。

**影響範囲**:
- pgvector statutes テーブルが **dummy 100 → 634,567 真法令 chunks** に置換。LanceDB 側は無変更。
- backend code 不変（retrieve dispatcher が pg を見るだけ）。
- 新規ファイル: `scripts/elaws_download.py` / `scripts/elaws_ingest_to_pgvector.py` / `scripts/probe_*.py` / `scripts/e2e_statute_check.py`。

**次の一手**:
- AGENTS.md / ARCHITECTURE.md の「623,000 件」表記を「~634k chunks / ~8.7k laws」に正確化。
- iOS `/rag/answer` 接続で end-to-end 検証（Ollama gemma3:27b 起動下で）。
- EC2 へ pgvector を pg_dump | restore でマイグレーション。
- Q-Map frontend を実 API に接続。

---

## 2026-06-09 — pgvector 移行 Phase B 着手 + データ実態の真相報告（劉 + Devin）

**何を**:
1. **接地データの真相を文書化**（重要）:
   - AGENTS.md / ARCHITECTURE.md は「法令 623,000 件 + 判例 724,443 件 (vectorized)」と記載していたが、
     LanceDB 実体を点検した結果、**判例は 724,443 件で正しい**が、**法令テーブル `elaws_v2` は 100 行のみ、
     かつ内容は "Test Law" / "sample text 0/1/2" のダミー**。実用法令 ingest は未実行。
   - 実体: precedents=724,443 / litigation=3,837 / elaws_v2=100 (dummy)。embed dim=384 (multilingual-e5-small)。
   - **harness L2 が法令を返さない原因は 2 つ**: (a) 上記 dummy しか無い、(b) `api.py` の `STATUTES_TABLE` 既定値が
     "statutes" だが実テーブル名は "elaws_v2"（恒常 mismatch、harness で常に statute 検索が None）。

2. **`api.py` の table 名 bug 修正**:
   - `PRECEDENTS_TABLE` / `STATUTES_TABLE` / `LITIGATION_TABLE` を env 上書き可に変更。
   - `STATUTES_TABLE` の既定値を `"statutes"` → `"elaws_v2"`（実体に合わせる）。

3. **pgvector スタックを Phase B として並列に立ち上げ**（既存 LanceDB は破壊しない、A/B 比較想定）:
   - `infra/docker-compose.pgvector.yml` 新規（pgvector/pgvector:pg16, host port **5435**）。
     既存 5432=db / 5433=sylvanexus_postgres / 5434=legalshield_postgres(GIS) と完全分離。
   - `infra/pgvector_init.sql` で precedents/statutes/litigation/etl_progress テーブル + pg_trgm を作成。
     HNSW 索引は ETL 完了後に CREATE する（INSERT 性能のため後付け）。
   - 起動確認: `vector 0.8.2`, `pg_trgm 1.6`。

4. **LanceDB → pgvector ETL 実装**:
   - `scripts/lance_to_pgvector.py`（pyarrow scanner + COPY FROM STDIN + 再開可能 etl_progress + 進捗ログ）。
   - 既知の障害修正: COPY 入力に NUL バイト (`\x00`) が含まれると PG が拒否 → `_escape_copy()` で除去。
   - 計測: COPY スループット ~3,000 rows/s（実測）。precedents 全量で 4 分前後の見込み。
   - elaws_v2 (100) / litigation (3,837) は本日完了。precedents (724,443) は本日中に完了予定。

5. **backend retrieve バックエンド抽象化**:
   - `legalshield/backend/pgvector_retrieve.py` 新規（cosine `<=>`、psycopg_pool 利用、harness.Source 互換）。
   - `api.py` に `LEGALSHIELD_RETRIEVE_BACKEND=lance|pg|auto` env flag を追加。
     - `lance` (既定): 従来路径 (後方互換)
     - `pg`: pgvector 強制（健康でなければ 503）
     - `auto`: pg 健康なら pg、ダメなら lance に fallback
   - `_select_retrievers()` で /rag/answer 内で透過に切替。harness L1-L7 はバックエンド非依存。
   - レスポンスに `retrieve_backend` を付加（観測用）。

6. **HNSW 索引方針**:
   - ETL 完了後 `python scripts/lance_to_pgvector.py --build-index` で `vector_cosine_ops, m=16, ef_construction=64`。
   - 線上 INSERT 可能なため運用時の追加 ingest を阻害しない。

**なぜ**:
- HiiForest infra ハンドオフを経て、Mac 帰任前に「基礎を正しく」の方針に切替。
- 将来の metadata + JOIN クエリ（taxonomy filter / NPO routing / 領域別検索）に SQL ネイティブの pgvector が有利。
- LanceDB はファイルベースで運用案件少なく、HNSW 索引再構築時にクエリが degrade する弱点あり。
- ただし即時切替はリスクなので「並列稼働 + env flag + A/B」で段階移行する。

**影響範囲**:
- backend code: `legalshield/backend/api.py`（retrieve dispatch + table 名 bug fix）+ `pgvector_retrieve.py`（新規）。
- infra: `infra/docker-compose.pgvector.yml`, `infra/pgvector_init.sql`（新規）。
- tooling: `scripts/lance_to_pgvector.py`（新規）。
- データ: pgvector に precedents 全量 + statutes(dummy 100) + litigation(3,837) を投入予定。LanceDB は無変更。
- iOS / harness 仕様は不変。env flag のみで挙動変更。

**E2E 検証手順（本セッション末）**:
```
docker compose -f infra/docker-compose.pgvector.yml up -d
python scripts/lance_to_pgvector.py --all
python scripts/lance_to_pgvector.py --build-index
$env:LEGALSHIELD_RETRIEVE_BACKEND="pg"; uvicorn legalshield.backend.api:app --port 8001
curl -X POST http://localhost:8001/rag/answer -H 'Content-Type: application/json' \
  -d '{"question":"パワハラで退職を強要された場合の対処は？","top_k":6}'
# 期待: result.retrieve_backend == "pg" / sources != [] / harness L1-L7 全層通過
```

**次の一手**:
- 法令本物 ingest（elaws v2）を RTX4080 で実行 → AGENTS.md の「623k 法令」を実体化。
- A/B 比較: 同一 question で lance vs pg の recall を比較する評価スクリプト。
- ETL を EC2 に持って行く（HiiForest infra ハンドオフ通り）: pgvector を EC2 に再構築 → `pg_dump` or 再 ETL。
- Q-Map frontend を実 API 接続 + emoji を SVG (chibi) marker に置換。

---

## 2026-06-02 (4) — コードベース棚卸し SYSTEM_OVERVIEW.md（劉 + Cascade）

**何を**: `SYSTEM_OVERVIEW.md` を新設。使用言語統計・資料夾構造・現有機能（iOS 30+ Services / backend 27 モジュール / crawlers / gis）・現有DB（LanceDB/PostGIS/judb/taxonomy）・主機&APP 開発総流程・HARNESS L1-L7 を1枚に棚卸し。AGENTS.md 索引に追加。ハンドブック PDF にも章追加。

**影響範囲**: ドキュメントのみ。

---

## 2026-06-02 (3) — 製品形態・UI同期・開発順序を明文化（劉 + Cascade）

**何を**: `DEPLOYMENT_TOPOLOGY.md` に §7b 製品形態 / §7c 同一DB・個別UI・同期・開発順序を追記。

**要点**:
- 「開発エージェント（AGENTS.md）」と「ユーザーに配る製品」は別物。GitHub は開発者だけ。
- 製品形態: 被害者=iOS App、NPO/弁護士=Webログイン、開発者=GitHub、（任意）完全ローカル=デスクトップ。
- 同一DB・個別UI は **API コントラクト（/api/v1/）+ モノレポ + 共有 taxonomy** で成立。
- 開発順序: ①APIコントラクト固定 → ②iOS MVP 縦貫通 → ③Web → ④Desktop。
- **当面の集中先 = iOS App を縦に貫通**（`LegalHarnessService` → 実 `/rag/answer` 接続）。

**影響範囲**: ドキュメントのみ。

**次の一手（合意できれば）**: iOS の `/rag/answer` 実接続、または API コントラクト仕様書の作成。

---

## 2026-06-02 (2) — デプロイ・トポロジ統合ドキュメント（劉 + Cascade）

**何を**:
- `DEPLOYMENT_TOPOLOGY.md` を新設。散在していた「環境間の同期」「LLM がどこで動くか」「DB をユーザーに配布できるか」「最新判例の API 連携」「NPO/弁護士の銜接」を 1 枚に統合。
- `AGENTS.md` の索引・リポジトリ地図に新規 doc と既存の散在 doc（戦略書・DEPLOYMENT_GUIDE・AGENT_HANDOFF）を追加して発見可能に。

**なぜ**:
- ユーザーの質問（RTX4080 訓練 / 別端末・協力者銜接 / Mac M1 の限界 / DB 配布 / 手機 vs PC で LLM をどこで走らせるか / 環境同期 / 最新データ API）に答え、散在情報を正準化するため。

**要点（回答の核）**:
- LLM の本格分析は**手機/M1 ではなくサーバ（Windows RTX4080 or AWS）**。手機は去識別化トリアージのみ。
- 訓練は 4080(16GB) で 3B LoRA 可（中核設計は `docs/strategy/2026-05-31_edge_training_and_role_architecture.md` に既存）。
- DB 配布は **API 方式（既定）** か **オフラインパック（curated subset・署名・版管理）**。
- 同期して良いのは**コード・docs・公開データ・モデル参照のみ。PII/証拠は同期しない**。

**影響範囲**: ドキュメントのみ。

**次の一手**: ハンドブック PDF を再生成（新 doc 反映）、GitHub バックアップ。

---

## 2026-06-02 — エージェント正準ドキュメント整備（劉 + Cascade）

**何を**:
- リポジトリ正準入口を新設: `AGENTS.md` / `ARCHITECTURE.md` / `PROGRESS.md`（本書）。
- 接地の絶対原則（RAG-First・harness L1-L7・幻覚禁止・「知らない」許容）を `AGENTS.md` §2 に明文化。
- Windsurf 自動ロード用ルール `.windsurf/rules/00-grounding.md` を追加。

**なぜ**:
- 別端末でのデプロイ / git pull / 新しい AI エージェントでも、**主架構と最新進捗と接地ルールを必ず読める**ようにし、開発の統一性と反幻覚を担保するため。

**影響範囲**: ドキュメントのみ（コード非変更）。全エージェントの作業開始手順が `AGENTS.md` 起点に統一。

**次の一手**: backend `/rag/answer` を iOS の事実回答経路の既定にする検証。GIS アップロード配線。

---

## 2026-06-01 — iOS ビルド復旧（Xcode 26 / iOS 26.5 SDK 対応）

**何を**: ビルド不能だった iOS アプリを**シミュレータ起動まで復旧**。

- **依存解決**: `mlx-swift` `0.18.1`→`0.25.6`、`mlx-swift-examples` `1.18.2`→`2.25.7`。
  - 旧 `0.18.1` は新 C++ libc++ で `std::allocator<const T>` 違反によりコンパイル不可。
  - `2.25.x` で product 名が `MLXLLM`（旧 `1.x` は `LLM`）。
- **deployment target**: iOS `16.0`→`17.0`（MLX 要件）。
- **未登録ファイル登録**: `HarnessModels.swift` / `LegalHarnessService.swift` / `HarnessAnswerView.swift` を `project.pbxproj` に手動登録（pbxproj が gitignore のため別端末の追加が未反映だった）。
- **SDK 厳格化対応**:
  - `CLLocationCoordinate2D: Codable` の二重定義を 1 箇所に統合（`ExportService` 側へ集約、`LocationAnonymizer` 側は削除）。
  - `AnonymizedLocation` に `Equatable` を手動実装。
  - MLX 2.x API 変更: `Chat(messages:)` 廃止 → `UserInput(chat: [Chat.Message])`、`promptTokens` が `[Int]` 化 → `.count`。
  - WhisperKit: `Float`→`Double` 明示変換（`segments` / `durationSec`）。
  - `@MainActor` 初期化子のデフォルト引数問題 → デフォルトを init 本体内に移動。
  - `AnonymizationLevel` を `public` 化。
- **署名/リソース**: `taxonomy_v1.json` が app ルートと `Resources/` に二重コピー（青フォルダ参照）→ CodeSign 失敗。Copy Bundle Resources からフォルダ参照を除去。

**結果**: iPhone 17 シミュレータ（iOS 26.5）で **install / launch 成功・稼働確認**。

**既知の落とし穴（次回のため）**:
- `project.pbxproj` / `Package.resolved` は gitignore。別端末では SPM 再解決とファイル登録要。
- ビルドは `-disableAutomaticPackageResolution -skipPackagePluginValidation -skipMacroValidation` を併用すると安定（package 編集を保持できる）。
- シミュレータ install で "Missing bundle ID" が出たら、署名（Info.plist binding）と taxonomy 重複を疑う。

**修正ファイル**:
- `ios/LegalShield/LegalShield/Services/{EmergencyEscalationService,ExportService,LocationAnonymizer,MLXOnDeviceProvider,VoiceTriageService,WhisperKitTranscriber}.swift`
- `ios/LegalShield/LegalShield.xcodeproj/project.pbxproj`（gitignore のため未追跡）

**次の一手**: 実機インストール（署名設定）、各機能（録音・LLM・証拠採取）のシミュレータ動作確認。

---

## 機能別ギャップ & 開発時程（2026-06-02 監査）

> 詳細は `ARCHITECTURE.md` §8。優先度順の概算時程。

| フェーズ | 内容 | 目安 |
|---|---|---|
| 1 | AWS 基盤実体化（EC2/Lambda+API GW+RDS/PostGIS）→ エンドポイント実体化 + GIS アップロード配線 + 本物の H3 化 + 地図可視化 | 2〜3 週 |
| 2 | 去識別化強化（日本語 NER で氏名・住所・電話マスク、文字起こしにも適用、犯罪情報 5W1H 構造化） | 2 週 |
| 3 | 音声パイプライン高度化（評価セット作成 → Whisper ドメイン適応学習 → CoreML 変換配備） | 3〜4 週 |
| 4 | NPO マッチング拡張（specialty/capacity/rating/contactLevel 追加 + 実データ + 写真/録音→トリアージ→推薦フロー結合） | 2 週 |

**合計: 約 9〜11 週（2〜3 ヶ月）**

---

*このログの上に新しいエントリを足していくこと。*
