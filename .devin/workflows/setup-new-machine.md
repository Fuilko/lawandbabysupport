---
description: LegalShield-jp を新しいマシンで軽量に立ち上げる（DB 大量データ除く）
---

# /setup-new-machine — 新マシン軽量セットアップ

このワークフローは、Windsurf 上で `/setup-new-machine` と入力すると順に実行する手順です。
**目的**: triage MVP（6 問問診 + 71 routes + DV センター 328 件）を 15〜25 分で起動する。

詳細解説は `docs/setup/QUICKSTART_NEW_MACHINE.md` を参照。

---

## Step 1. 前提を確認

ユーザーに以下を聞く（または自分で確認）：

- Docker Desktop が起動しているか？ → `docker info` で確認
- 作業ディレクトリは `LegalShield/` のルートにいるか？
- git clone は完了しているか？

不足があれば、ユーザーに指示。

---

## Step 2. `.env` をテンプレからコピー

`.env` がなければ作成。secrets は含まれていないのでこのまま動く。

// turbo
```pwsh
if (-not (Test-Path gis\.env)) {
  Copy-Item gis\.env.example gis\.env
  "created gis/.env"
} else {
  ".env already exists, skipped"
}
```

---

## Step 3. Docker compose で 3 コンテナを起動（postgres + api + frontend）

初回は image build に 3〜5 分かかる。

```pwsh
docker compose -f gis\docker-compose.local.yml up -d --build
```

完了したら状態を確認：

// turbo
```pwsh
docker compose -f gis\docker-compose.local.yml ps
```

期待: 3 サービスとも `running (healthy)` または `Up`。

---

## Step 4. ヘルスチェック

API が応答するか確認。最大 30 秒待ってから：

// turbo
```pwsh
Start-Sleep -Seconds 5
Invoke-RestMethod http://localhost:8090/health
```

routing seed が入っているか確認（**71 件**が出れば OK）：

// turbo
```pwsh
docker exec legalshield_postgres psql -U legalshield -d legalshield -c "SELECT COUNT(*) AS routes FROM legalshield.category_routing;"
```

---

## Step 5. 軽量 ingest — DV センター 328 件のみ

PDF 1 ファイル（284 KB）→ 328 行。

// turbo
```pwsh
docker exec legalshield_api pip install --quiet pdfplumber
docker exec legalshield_api python -m ingest.ingest_dv_centers
```

検証：

// turbo
```pwsh
docker exec legalshield_postgres psql -U legalshield -d legalshield -c @"
SELECT COUNT(DISTINCT prefecture_code) AS prefs, COUNT(*) AS rows
  FROM legalshield.support_org WHERE source = 'naikakufu_dv';
"@
```

期待:
```
 prefs | rows
-------+------
    47 |  328
```

---

## Step 6. ブラウザで動作確認

ユーザーに `http://localhost:8092` を開いてもらう。最低でも以下を見て：

1. **🚨 緊急ボタン**を押す → 緊急バナー + `#8008` の tel: リンク
2. **🛟 相談タブ**で 6 問答えて tier カードが出る
3. **🗺️ 地図タブ**で東京付近の DV センター点が見える

問題があれば、`docker logs legalshield_api` でログ確認。

---

## Step 7. 進捗ノートと残課題の同期

最後に、現状を確認するため：

// turbo
```pwsh
git -C . log --oneline -5
git -C . status --short
```

`docs/strategy/2026-05-26_dev_progress.md` の **第 7 章「残課題」** を開いて、次に着手するタスクをユーザーと相談。

---

## 失敗時のロールバック

何かおかしいとき、postgres volume を捨てて完全にやり直す：

```pwsh
docker compose -f gis\docker-compose.local.yml down -v
docker compose -f gis\docker-compose.local.yml up -d --build
```

> ⚠️ `-v` で volume を消すため、ingest 済みデータも全部消える。再 ingest が必要。

---

## このワークフローでやらないこと（重要）

以下は **ユーザーが明示的に頼まない限り** 実行しない：

- e-Stat 犯罪統計の取込（数百 MB〜GB、API キー必要）
- N03 行政界 shapefile（200 MB+）
- 法テラス CSV（公式 CSV 手動取得必要）
- SLM / GPU 周辺の build
- vector DB（LanceDB）構築
- `private/` 配下のデータ転送

理由：新マシンの初期立ち上げを軽量に保つため。これらが必要になったときは、別 workflow で個別に走らせる。
