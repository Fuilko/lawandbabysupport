# AGENTS.md — AI エージェント正準入口（Single Source of Truth Index）

> **このファイルは、どの端末・どの AI エージェント（Cascade / Claude / Cursor / Copilot 等）でも、
> リポジトリを開いたら最初に読むべき正準入口です。**
> git clone / pull 後、作業開始前に必ず本ファイルと §1 のリンク先を読むこと。
>
> Repo: `Fuilko/lawandbabysupport` · Branch: `main` · Maintainer: 劉 建志 (LIU CHIEN CHIH)

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
| 1 | **`AGENTS.md`**（本書） | エージェント入口・行動規範・索引 |
| 2 | **`ARCHITECTURE.md`** | システム主架構（iOS / backend / GIS / RAG）の唯一の真実 |
| 3 | **`PROGRESS.md`** | 最新開発進捗ログ（時系列・追記式） |
| 4 | `docs/AGENT_SKILL_BOUND_DESIGN.md` | 幻覚防止 / 能力境界の設計指針 |
| 5 | `legalshield/backend/harness.py` | 反幻覚ハーネス L1〜L7 実装（接地の中核） |
| 6 | `README.md` | プロジェクト概要（三言語） |

> **重要**: 上記より新しい情報は常に `PROGRESS.md` の最上部にある。
> 過去のチャット要約や記憶より、**リポジトリ内のこれらのファイルを正とする**。

---

## 2. 接地の絶対原則（Anti-Hallucination / 幻覚禁止）

LegalShield の法律・医療出力は、**LLM の生成知識ではなく、必ずデータベース / ベクトル検索から取得した根拠に接地**しなければならない。

### 2.1 RAG-First（検索優先）— 強制
- 法令・判例・支援機関・統計に関する事実主張は、**`/rag/answer` エンドポイント（`harness.py`）経由**で行う。
- raw LLM（`/api/generate` 等）を**事実回答に直接使ってはならない**。失敗時のみ明示フラグ付きで fallback。
- 根拠 DB:
  - 国法 **623,000 件** + 判例 **724,443 件**（ベクトル化済み）
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
