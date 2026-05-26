# LegalShield-jp — AI Agent Handoff（新マシン用）

このファイルは、新しい環境で **Windsurf / Cursor / Claude Code 等の AI アシスタント** を初めて立ち上げたとき、**そのままプロンプトに貼る**ためのコンテキスト要約です。

---

## あなた（AI）が知っておくべきこと

### プロジェクトの概要

**LegalShield-jp** は、日本の市民が直面する 12 種類の法的・社会的問題（DV、児童虐待、ハラスメント、製品欠陥、行政の不当対応など）について、**最適な相談先を 6 問の問診から導く**公益 GIS / triage プラットフォーム。

- **倫理基盤**: 中立的ツール提供者。特定事案への法的助言はしない。匿名利用前提。
- **同意ラダー T0〜T4**: 端末完結 → 統計化 → 個人化助言 → 詳細記録 → 第三者共有、の 5 段階で漸進的にユーザーから同意を取る。
- **資金獲得状況**: トヨタ財団 / RISTEX SOLVE 2026 へ提案中。担当アドバイザーは鈴木教授。

### 技術スタック

| 層 | 採用技術 |
|---|---|
| DB | PostGIS 15 / 3.3（Docker） |
| API | Python 3.11 + FastAPI + SQLAlchemy 2.x asyncpg |
| Frontend | Vanilla JS + Leaflet（ビルド不要） |
| Ingest | httpx + pdfplumber（必要時のみ） |
| LLM | 当面 rule-based、後日 Phi-3.5 / Gemma-3-1B のオンデバイス推論 |
| Infra | EC2（hiiforest と共用 postgres）+ host nginx vhost |

### 現在の進捗（2026-05-26 時点）

- ✅ Day 1〜5 完了。**triage MVP が動作**（71 routes / 12 categories）
- ✅ DV センター 328 件 / 全 47 都道府県を投入済み
- ✅ Help 記事 3 本（dv / product-defect / admin-grievance）
- ✅ Hotline 検証ノート（16 件、出典付き）
- 🚧 残課題は `docs/strategy/2026-05-26_dev_progress.md` の第 7 章

---

## 新マシンで最初にやること（あなたへの指示）

ユーザーが「セットアップして」と言ったら、以下の順で実行：

1. **`docs/setup/QUICKSTART_NEW_MACHINE.md` を読む**
2. ユーザーに以下を確認する：
   - Docker Desktop は起動済みか？
   - `gis/` ディレクトリは clone 済みか？
   - `.env` ファイルは作成済みか？（なければ `.env.example` から copy）
3. `docker compose -f gis/docker-compose.local.yml up -d --build` を実行
4. ヘルスチェック：`curl http://localhost:8090/health`
5. DV ingest（軽量データ）：`docker exec legalshield_api python -m ingest.ingest_dv_centers`
6. ブラウザで `http://localhost:8092` を開いてもらい、動作確認

**重い ingest（e-Stat / N03 / 法テラス CSV）は、ユーザーが明示的に頼まない限り走らせない。**

---

## 守るべきルール

### コード品質

- **コメント・docstring を勝手に削除しない**。既存の英文 docstring は意図的に残してあるもの。
- **テストを削除・弱体化しない**。
- **依存ライブラリを勝手に追加しない**。`gis/services/legalshield-api/requirements.txt` を変更するときは必ずユーザーに確認。
- **既存の design philosophy に従う**：
  - 匿名性ファースト（IP は記録しない、`client_hash` のみ）
  - graceful degradation（DB 書き込み失敗してもユーザー向け応答は返す）
  - 公的データソースを優先（NPO 二次情報より省庁公式）

### セキュリティ・プライバシー

- 🔒 `private/mapry_ai/` 以下の内容は **絶対に commit しない**（`.gitignore` で守られている）。
- 🔒 `.env` を git に追加しない。
- 🔒 ユーザーの実名・住所・電話番号・案件詳細を発言・コミットメッセージに含めない（プロジェクトの倫理綱領）。
- 🔒 加害者の個人情報を含むファイル名・URL を生成しない。

### コミットメッセージ

- 機能追加：`feat(scope): summary`
- バグ修正：`fix(scope): summary`
- ドキュメント：`docs(scope): summary`
- データ：`data(scope): summary`
- scope 例：`gis`, `intake`, `ingest`, `frontend`, `db`

### 言語

- ユーザーとは **日本語** または **繁体中文**（コードコメントは英語可）。
- ユーザーは日本語・中国語・英語を理解する。指示があった言語に揃える。

---

## トラブルシューティング 3 大パターン

### 1. Postgres コンテナが起動しない

```pwsh
docker logs legalshield_postgres
# よくある原因: ポート 5434 が他のプロセスに占有 → docker-compose.local.yml の DB_HOST_PORT を変更
```

### 2. API コンテナが restart loop

```pwsh
docker logs --tail 100 legalshield_api
# よくある原因:
#  (a) DATABASE_URL の型ヒント不一致 → .env を確認
#  (b) requirements.txt に追加したパッケージのビルド失敗 → image を rebuild
```

### 3. Frontend で 404 / 緊急バナーが出ない

- `frontend/index.html`、`frontend/intake.js`、`frontend/style.css` のいずれかが壊れている可能性
- ブラウザの devtools console を見る
- nginx は ro マウントなので、ホストでファイルを保存し直すだけで反映される

---

## ユーザーから「これを次にやって」と言われたとき優先するもの

1. `docs/strategy/2026-05-26_dev_progress.md` の第 7 章「残課題」に挙げられているもの
2. `docs/ops/2026-05-26_hotline_verification.md` の ToDo 欄
3. 上記が完了したら、`/docs/help/` 配下に追加する記事（残り 9 categories 分）

これ以外の作業（特に大規模リファクタ、新規ライブラリ導入、UI 全面刷新）は **ユーザーが明示的に依頼しない限り提案しない**。

---

## このプロジェクトの「やってはいけない」リスト

- ❌ 法律的な助言を生成する（あくまで「相談先案内」のみ）
- ❌ ユーザーの個人情報を要求・保存する設計を入れる
- ❌ 加害者・被告とされる個人・法人の名前を hardcode する
- ❌ Mapry 案件の事実関係を LegalShield 側のコードに混ぜる（完全に切り分け）
- ❌ 同意ラダーを **逆順で実装する**（T4 を T0 より先に作る等）
- ❌ 「自動通報」「自動訴訟」のような暴走機能（あくまで人間が判断）

---

最後に：このプロジェクトは個人開発で、社会的にデリケートな領域を扱う。**慎重に、誤情報を出さず、ユーザーの選択肢を狭めない**ことを最優先に。
