---
trigger: always_on
---

# LegalShield 接地・統一性ルール（常時適用）

本リポジトリで作業する全 AI エージェントは、作業開始前に以下を必ず実行する。

## 1. 正準ドキュメントを読む（作業開始時）
1. `AGENTS.md` — エージェント入口・行動規範・索引
2. `ARCHITECTURE.md` — システム主架構（唯一の真実）
3. `PROGRESS.md` — 最新進捗（最上部が最新。**過去の記憶より優先**）

## 2. 反幻覚・接地（絶対）
- 法律・医療の事実主張は **必ず RAG / DB から取得した根拠に接地**する。
  backend `/rag/answer`（`legalshield/backend/harness.py` の L1-L7）経由を既定とする。
- raw LLM（`/api/generate` 等）を事実回答に直接使わない。失敗時のみ明示フラグ付き fallback。
- 出典が無い・確信が無い場合は **編造せず「不明」「要弁護士確認」** と答える。
- 4 禁止: ①出典未確認の踏襲 ②DB があるのに再検索を怠る ③反証ステップ欠落 ④流暢さを事実精度より優先。

## 3. プライバシー
- センシティブデータはローカル優先。位置情報は `LocationAnonymizer` で去識別化後に送信。
- 全助言に法源 / 医学ガイドラインの出典を強制付記。

## 4. 開発の統一性（作業終了時）
- `PROGRESS.md` の最上部に日付つきエントリを追記（何を・なぜ・影響範囲・次の一手）。
- 架構を変えたら同一コミットで `ARCHITECTURE.md` を更新。
- 既存配置（`docs/` `legalshield/` `gis/` `ios/`）を尊重。
- `ios/**/project.pbxproj` と `Package.resolved` は gitignore。依存・ファイル追加は端末ごとに再設定要。
