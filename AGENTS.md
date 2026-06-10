# AGENTS.md — AI エージェント正準入口（Single Source of Truth Index）

> **このファイルは、どの端末・どの AI エージェント（Cascade / Claude / Cursor / Copilot 等）でも、
> リポジトリを開いたら最初に読むべき正準入口です。**
> git clone / pull 後、作業開始前に必ず本ファイルと §1 のリンク先を読むこと。
>
> Repo: `Fuilko/lawandbabysupport` · Branch: `main` · Maintainer: 劉 建志 (LIU CHIEN CHIH)

> 
> **HIIFOREST 合同会社 portfolio context**: HIIFOREST 配下には ① SylvaNexus（林業 SaaS）② LegalShield（本書）③ HII Forensics（UAV 鑑定）の三事業がある。
> **作業前にまず `PORTFOLIO.md`（本 repo 直下 / `D:\projects\PORTFOLIO.md`）を読み**、その後に本 AGENTS.md を読むこと。
> クロス領域機能（林業 GIS / UAV log 解析等）は redirect、reimplement しないこと。

---

## 0. ミッション（絶対に逸脱しない）

**デジタル賦権** — AI 駆動の法律自救 + 婦幼医療補助プラットフォームで、**法律弱者・医療弱者を守る**。

- **LegalShield (法盾)**: 証拠保全 → 戦略シミュレーション → 文書生成 → 専門家紹介
- **PocketMidwife (口袋助産士)**: 症状問診 → Edge AI 検傷 → Triage → 救急紹介

本ミッションに反する出力（未検証の法的助言、幻覚による事実主張）は**致命的脅威**として扱う。

---

## 1. 作業前に必ず読む（正準ドキュメント）

| 順 | ファイル | 内容 |
|---|---|---|
| 0 | **`D:\projects\PORTFOLIO.md`** | **Portfolio Index — 3 製品線（①SylvaNexus / ②LegalShield / ③HII Forensics）の正準入口。本書 AGENTS.md より先に読む。** mapry 案など実際の case data は ③b `D:\projects\flylog_analysis` にあり、本書 ②a の context だけでは分析不能。 |
| 1 | **`AGENTS.md`**（本書） | エージェント入口・行動規範・索引（②a 範囲） |
| 2 | **`ARCHITECTURE.md`** | システム主架構（iOS / backend / GIS / RAG）の唯一の真実 |
| 3 | **`PROGRESS.md`** | 最新開発進捗ログ（時系列・追記式） |
| 4 | **`DEPLOYMENT_TOPOLOGY.md`** | 環境・同期マトリクス・DB配布・5ロール銜接（統合マスター）|
| 4b | **`SYSTEM_OVERVIEW.md`** | 現有機能・資料夾構造・使用言語・DB・開発総流程・HARNESS（棚卸し）|
| 5 | `docs/strategy/2026-05-31_edge_training_and_role_architecture.md` | エッジ訓練(RTX4080)・5ロール・障害分離の中核設計 |
| 6 | `docs/AGENT_SKILL_BOUND_DESIGN.md` | 幻覚防止 / 能力境界の設計指針 |
| 7 | `legalshield/backend/harness.py` | 反幻覚ハーネス L1〜L7 実装（接地の中核） |
| 8 | `DEPLOYMENT_GUIDE.md` / `docs/setup/AGENT_HANDOFF.md` | 環境再構築 / 協力者ハンドオフ |
| 9 | `README.md` | プロジェクト概要（三言語） |

> **重要**: 上記より新しい情報は常に `PROGRESS.md` の最上部にある。
> 過去のチャット要約や記憶より、**リポジトリ内のこれらのファイルを正とする**。

---

## 2. 接地の絶対原則（Anti-Hallucination / 幻覚禁止）

LegalShield の法律・医療出力は、**LLM の生成知識ではなく、必ずデータベース / ベクトル検索から取得した根拠に接地**しなければならない。

### 2.1 RAG-First（検索優先）— 強制
- 法令・判例・支援機関・統計に関する事実主張は、**`/rag/answer` エンドポイント（`harness.py`）経由**で行う。
- raw LLM（`/api/generate` 等）を**事実回答に直接使ってはならない**。失敗時のみ明示フラグ付きで fallback。
- 根拠 DB:
  - 国法 **634,567 chunks / 8,732 法令** + 判例 **724,443 chunks**（ベクトル化済み・pgvector 5435 / LanceDB 両系統）。「623k」は旧表記、実体 chunk 数は 634k（2026-06-09 確定）。
  - `docs/research/precedents/*.jsonl`（判例 RAG コーパス）
  - GIS: PostGIS（DV センター・犯罪統計・法テラス・行政界）→ `gis/`

### 2.2 反幻覚ハーネス L1〜L7（`harness.py`）を必ず通す
```
L1 Intent & Risk Classifier   — 意図・リスク（不可逆操作は弁護士強制）
L2 Mandatory Retrieval Gate   — 必須検索（判例+法令を取得、未取得なら生成禁止）
L3 Variable-loaded Reasoning  — context-pack 装填
L4 Constrained Generation     — source-tag 付き / refusal-aware（出典なきは「不明」）
L5 Self-verification          — claim 抽出 → retrieval match → judge
L6 Transparency payload       — source tag / confidence / risk badge / lawyer trigger
L7 Audit Log                  — SHA-256 chain
```

### 2.3 4 つの禁止失敗パターン（2026-05-28 の教訓）
1. **Hallucination cascade** — 他 AI の記述を出典確認せず踏襲（禁止）
2. **Context illusion** — DB が使えるのに再 retrieval を怠る（禁止）
3. **Confirmation bias > Falsification** — 反証ステップ欠落（禁止）
4. **Narrative coherence > Factual precision** — 流暢さを事実精度より優先（禁止）

### 2.5 利用者証拠優先原則（2026-06-09 追加・**最重要**）

**事案分析を行う前に、利用者が提供した証拠フォルダを完全に読み終えること。** 未読のファイルの中身を「推測」「要約信頼」で進めることは**致命的接地失敗**である。

**強制ゲート**: `legalshield/backend/evidence_gate.py` を案件分析の前段（L0）として用いる。
```python
from legalshield.backend import evidence_gate as eg
manifest = eg.load_manifest(Path("private/<case>/evidence_manifest.json"))
eg.assert_ready_for_analysis(manifest, min_coverage=0.90)  # ←これが通らないと L1 に進めない
```

**v1.1 改良 (2026-06-09): File Role / Priority 分類**

evidence_gate v1.0 では「全ファイル必読」設計だったため、forensic raw data
(ext4 image, raw GPS log, syslog 等) も「未読」扱いになり利用者から
「raw data は forensic agent 専用、LegalShield agent は分析報告だけ読めばよい」
と指摘された。v1.1 で `FileRole` 分類を導入:

| Role | 例 | LegalShield agent の責務 |
|---|---|---|
| `REPORT` | DEEP_ANALYSIS.md, FORENSIC_REPORT.pdf, MASTER_REPORT.md | **必読** |
| `EVIDENCE_DOC` | 契約書, 内容証明, .eml, 甲号証, 注文書 | **必読** |
| `META` | PORTFOLIO.md, README.md, AGENTS.md, manifest.json | **必読** |
| `RAW_DATA` | drone_ext4_backup.img, raw_extracts/*.txt, *.bag, *.tlog | **対象外**（forensic agent 専用） |
| `VISUALIZATION` | trajectory_3D.png, flight_map.html, overlays/* | サンプル 1 件で OK |
| `SCRIPT` | analyze_*.py, *.sh, *.cpp | 読不要（出力 .md を読む） |

**coverage 計算は REPORT + EVIDENCE_DOC + META のみ**で行う。
`classify_role(relpath)` がパターンマッチで自動分類、`RAW_DATA` / `SCRIPT` は
auto-mark_read される（agent の確認不要）。

**3 製品線が連動する案件**（例: ③b 飛行鑑識 + ②a 法律分析）では、
③b に raw data + 鑑識報告を置き、②a の LegalShield agent は
③b の **報告 .md / .pdf のみ** を読み込めばよい。

**運用ルール**:
1. 案件 dir に **`evidence_manifest.json`** を必ず作る（`eg.index_evidence_folder()`）
2. agent が中身を実際に読んだら **`eg.mark_read()`** で記録する
3. 全分析報告の先頭に **`eg.coverage_banner()`** を挿入する（透明性 metric 必須表示）
4. **coverage < 90% で分析を始めてはならない**（OCR・vision・別ツール援用してでも 90% を超えさせる）
5. 「要約ファイル（json/md/chat ログ）を読んだから原本未読でも OK」は**禁止**。要約と原本に乖離がある可能性を前提に、原本を必ず確認する

**この原則は 2026-06-09 mapry 案で：**
- 53 件の証拠のうち実際に読んでいたのは 9 件（17%）だった
- 残り 44 件には mapry 弁護士の回信（1.6MB scan PDF）、委任書、最終要求書、7 件の脅迫メール原文、18 件の証拠写真などが含まれていた
- 既存ファイルの要約だけで「全面分析」を生成し、訴訟当事者構造（媒介代理店 vs 売買契約、買主は劉氏ではなく正昌）も含めて根本的に誤った報告書を作ってしまった
- このような失敗を構造的に防ぐためにこの §2.5 と evidence_gate を導入する

---

### 2.4 「知らない」を選べ
出典が無い・確信が無い場合は、**編造せず「不明」「要弁護士確認」と回答する**こと。

---

## 3. プライバシー原則（去識別化）
- センシティブデータは**ローカル優先処理**。サーバは生データを保持しない。
- 位置情報は `LocationAnonymizer`（hex 化 / 仮想都市変換 / オフセット）で去識別化してから送信。
- 研究 / GIS アップロードは差分プライバシー（Laplace ノイズ）+ 暗号化。
- 全助言に**法源または医学ガイドラインの出典を強制付記**。

---

## 4. 開発の統一性ルール（全エージェント共通）

1. **作業開始時**: `AGENTS.md` → `ARCHITECTURE.md` → `PROGRESS.md` を読む。
2. **作業終了時**: `PROGRESS.md` の最上部に日付つきエントリを追記（何を・なぜ・影響範囲）。
3. **アーキ変更時**: `ARCHITECTURE.md` を同一 PR/コミットで更新。
4. **接地**: 法律・医療の事実は §2 の RAG/harness 経由。逸脱しない。
5. **既存構造を壊さない**: `docs/` `legalshield/` `gis/` `ios/` の配置を尊重。
6. **gitignore 注意**: `ios/**/project.pbxproj` と `Package.resolved` は git 管理外。
   依存・ファイル追加は各端末で再設定が必要（手順は `ARCHITECTURE.md` §iOS 参照）。
7. **新しい LLM への移行**: プロバイダ抽象（`LLMProvider`）の背後で差し替え、harness は不変。

---

## 5. リポジトリ地図（主要ディレクトリ）

```
lawandbabysupport/
├── AGENTS.md              ← 本書（エージェント入口）
├── ARCHITECTURE.md        ← 主架構の唯一の真実
├── DEPLOYMENT_TOPOLOGY.md ← 環境/同期/DB配布/5ロール（統合マスター）
├── DEPLOYMENT_GUIDE.md    ← 環境再構築の詳細手順
├── PROGRESS.md            ← 最新進捗ログ（追記式）
├── README.md              ← 概要（三言語）
├── ios/LegalShield/       ← iOS アプリ（SwiftUI + MLX on-device LLM + WhisperKit）
├── legalshield/
│   ├── backend/           ← harness.py(L1-L7) / 埋め込み / heatmap / API
│   ├── crawlers/          ← 法令・判例・統計・支援機関クローラ
│   └── dispatch/          ← tier_engine（緊急度ルーティング）
├── gis/                   ← PostGIS + ingest + Leaflet フロント（Q-Map）
├── data/case_taxonomy/    ← 案件分類スキーマ（taxonomy_v1.json）
├── docs/                  ← 設計書・判例 RAG コーパス・助成金資料
├── aws/                   ← AWS インフラ設定
└── .windsurf/             ← Windsurf workflows / rules（自動ロード）
```

---

*最終更新: 2026-06-02 — このファイルが古い場合は `PROGRESS.md` を正とすること。*
