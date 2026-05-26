# 新しいマシンで LegalShield-jp を立ち上げる — Quickstart（軽量版）

**所要時間**: 15〜25 分（Docker 起動済みなら）
**ゴール**: triage MVP（6 問問診 + DV センター 328 件 + 全 71 routes）が `http://localhost:8092` で動くところまで。
**スコープ外**: e-Stat 犯罪統計の大量取込・N03 行政界 shapefile・SLM ベクトル DB・Mapry private データ。これらは **重い** ので新マシンの初期セットアップでは入れない。

---

## 0. 前提（事前にインストール）

| ツール | バージョン | 用途 |
|---|---|---|
| **Docker Desktop** | 24.x 以降 | postgres / API / frontend を全部 docker で動かす |
| **Git** | 2.40+ | リポジトリ取得 |
| **Python**（任意） | 3.11 | ローカルで md→pdf 等のスクリプトを動かす場合のみ |
| **VS Code + Windsurf**（任意） | — | このリポジトリの slash command `/setup-new-machine` を使う場合 |

> 💡 Python はホストにインストールしなくても OK。ingest スクリプトは全て `docker exec legalshield_api python -m ...` の形で API コンテナ内で走らせる。

---

## 1. リポジトリを取得

```pwsh
# Windows (PowerShell) — どこか作業用ディレクトリで
git clone https://github.com/Fuilko/lawandbabysupport.git LegalShield
cd LegalShield
```

```bash
# macOS / Linux
git clone https://github.com/Fuilko/lawandbabysupport.git LegalShield
cd LegalShield
```

---

## 2. 環境変数ファイルを用意

```pwsh
Copy-Item gis\.env.example gis\.env
```

```bash
cp gis/.env.example gis/.env
```

**そのままで動く**。秘密情報は含まれていない（パスワードもローカル開発用）。e-Stat / AWS の API キー欄は空のままで OK — 軽量版ではいずれも使わない。

---

## 3. Docker でフルスタック起動

```pwsh
cd gis
docker compose -f docker-compose.local.yml up -d --build
```

3 つのコンテナが立ち上がる：

| コンテナ | ポート | 役割 |
|---|---|---|
| `legalshield_postgres` | `5434:5432` | PostGIS 15 / PostGIS 3.3 |
| `legalshield_api`      | `8090:8080` | FastAPI（routing + intake + nearest-support）|
| `legalshield_frontend` | `8092:80`   | nginx + 静的ファイル（Leaflet + intake.js）|

初回ビルドは 3〜5 分。Postgres の init は `gis/db/001_init_schema.sql`〜`003_routing_seed_more.sql` を自動適用するので **スキーマ作成も終わっている**。

### 動作確認

```pwsh
# API が立ち上がっているか
Invoke-RestMethod http://localhost:8090/health

# Frontend
Start-Process http://localhost:8092

# routing seed が入っているか（71 routes になっていれば OK）
docker exec legalshield_postgres psql -U legalshield -d legalshield -c "SELECT COUNT(*) FROM legalshield.category_routing;"
```

---

## 4. 軽量 ingest — DV 相談支援センター 328 件のみ

「軽量版」のスコープでは、外部から落とすデータは **これ 1 件だけ**：

```pwsh
# host 経由でファイル落とし、コンテナ内の python で展開（pdfplumber 必要）
docker exec legalshield_api pip install --quiet pdfplumber
docker exec legalshield_api python -m ingest.ingest_dv_centers
```

成功すれば最後の行に：
```
INFO legalshield.ingest: dv_center ingest done: in=328 out=328
```

**サイズ感**: PDF 284 KB、postgres 上のレコード 328 行。LANGSAM。

### 検証

```pwsh
# 47 都道府県すべて埋まっているか
docker exec legalshield_postgres psql -U legalshield -d legalshield -c "
  SELECT COUNT(DISTINCT prefecture_code) AS prefs, COUNT(*) AS rows
    FROM legalshield.support_org WHERE source = 'naikakufu_dv';"

# 期待:
#  prefs | rows
# -------+------
#    47  |  328
```

---

## 5. ブラウザで MVP を触る

`http://localhost:8092` を開く。

- **🚨 緊急ボタン** → 即 `#8008` / 110 が出る
- **🛟 相談タブ** → 6 問問診 → tier カード推奨
- **🗺️ 地図タブ** → 現在地リスク + 最寄り支援検索（DV センター点在）

代表的なシナリオは `docs/strategy/2026-05-26_dev_progress.md` の第 8 章参照。

---

## 6. 軽量版でやらないこと（明示的に除外）

新マシンの初期セットアップでは、以下を **意図的にやらない**。必要に応じて後日：

| やらないもの | 理由 | やる場合 |
|---|---|---|
| **e-Stat 犯罪統計の取込** | 数百 MB〜GB、API キー要 | `docker exec legalshield_api python -m ingest.ingest_estat_crime` |
| **N03 行政界 shapefile** | 200 MB+、ローカル PostGIS が膨らむ | `docker exec legalshield_api python -m ingest.ingest_n03_boundaries` |
| **法テラス CSV** | 公式 CSV を手動取得する必要あり | `--csv` で渡す |
| **SLM / Phi-3.5 / Gemma-3-1B** | 1〜3 GB、推論用 GPU 推奨 | 別 issue 進行中 |
| **Mapry case AI**（private/）| 秘匿データ、別マシンへの移管は別手順 | `private/mapry_ai/` は `.gitignore` で完全除外 |
| **vector DB (LanceDB)** | 数 GB | 当面 rule-based で十分 |

---

## 7. うまく動かないときのデバッグ手順

```pwsh
# 1) コンテナの状態
docker compose -f gis\docker-compose.local.yml ps

# 2) API のログ（直近 50 行）
docker logs --tail 50 legalshield_api

# 3) DB が空っぽに見えたとき：マイグレーションが走っていない
#    → volume を捨ててやり直す
docker compose -f gis\docker-compose.local.yml down -v
docker compose -f gis\docker-compose.local.yml up -d --build

# 4) フロントの変更が反映されない
#    → nginx は volume ro マウントなので、ファイル保存だけで OK。
#       ブラウザ側のキャッシュを Shift+F5 で破棄。

# 5) intake の SQL エラーが出る
docker exec legalshield_postgres psql -U legalshield -d legalshield -c "\dt legalshield.*"
# 期待: problem_category, category_routing, support_org, intake_session, …
```

---

## 8. 新マシンで開発を続ける場合のチェックリスト

- [ ] `git config user.name` / `user.email` をこのマシン用に設定
- [ ] `git pull` で最新を取得（出張中に CI からの変更があるかもしれない）
- [ ] `docs/strategy/2026-05-26_dev_progress.md` の **第 7 章「残課題」** を確認、次に着手すべきものを 1 つ in_progress に
- [ ] `docker compose -f gis/docker-compose.local.yml up -d` を起動状態にしてからエディタを開く
- [ ] Windsurf を使う場合：`/setup-new-machine` slash command で自動化版を実行できる（`.windsurf/workflows/setup-new-machine.md`）

---

## 9. データ同期戦略（複数マシンを行き来する場合）

| データ | 同期方法 |
|---|---|
| **コード**（gis/, docs/, scripts/） | git push/pull のみ |
| **データベース内容** | 各マシンで `ingest.ingest_dv_centers` を再実行（PDF は upstream から取得）|
| **生 PDF / 大きなデータ** | 落とし直しで OK（gitignore 済み）|
| **Mapry private データ** | 暗号化 USB か WireGuard 経由で手動コピー。git には絶対に乗せない |
| **secrets** | `.env` は git 管理外。1Password / Bitwarden 等のパスマネで共有 |

> 🔐 `.env` を **git に追加してはいけない**。秘密情報を入れる用途に拡張するため、現状ダミー値であっても commit 禁止。

---

## 10. ロールバック・引っ越しが完了した後

1. 旧マシンの docker volume は **必要なければ削除** してディスクを空ける：
   ```pwsh
   docker compose -f gis\docker-compose.local.yml down -v
   docker system prune -af
   ```
2. 旧マシンの `private/` は **暗号化 USB に移すか、シュレッダー** して消す
3. 旧マシンの GitHub credential / 1Password セッションをログアウト

---

## 付録：Agent（Windsurf / Claude Code 等）に渡すハンドオフ

新マシンで AI コーディングアシスタント（Windsurf, Cursor, Claude Code 等）を初めて立ち上げるとき、**そのままコピペしてプロンプトに貼る**用の要約は `docs/setup/AGENT_HANDOFF.md` に置いてある。

Windsurf を使う場合は、左ペインのチャットで `/setup-new-machine` と打つだけで、上記の手順を自動で順に実行してくれる（要承認の destructive コマンドだけ手動）。
