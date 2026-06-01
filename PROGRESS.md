# PROGRESS.md — 開発進捗ログ（追記式・最新が上）

> **運用ルール**: 作業を終えたら、このファイルの最上部（日付見出しの直後）に新エントリを追記する。
> 書式: 日付 / 担当 / 何を・なぜ・影響範囲・次の一手。
> 入口は `AGENTS.md`、架構は `ARCHITECTURE.md`。**過去のチャット記憶より本ファイルを正とする。**

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
