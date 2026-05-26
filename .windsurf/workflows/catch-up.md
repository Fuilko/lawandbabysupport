---
description: 久しぶりにこのプロジェクトを触るとき、現状と次にやるべきことを把握する
---

# /catch-up — 現状を把握して次の一手を決める

新マシンに移った直後や、数日離れた後の最初のセッションで実行。

## Step 1. 最新を取得

// turbo
```pwsh
git -C . pull --ff-only
git -C . log --oneline -10
git -C . status --short
```

## Step 2. 最新の進捗ドキュメントを読む

順に開いて目を通す：

1. `docs/strategy/2026-05-26_dev_progress.md` — 直近スプリント全体像と残課題
2. `docs/ops/2026-05-26_hotline_verification.md` — hotline 検証 TODO
3. `docs/setup/AGENT_HANDOFF.md` — エージェント向けプロジェクト要約

## Step 3. スタックを起動

// turbo
```pwsh
docker compose -f gis\docker-compose.local.yml up -d
Start-Sleep -Seconds 3
docker compose -f gis\docker-compose.local.yml ps
```

## Step 4. DB のレコード数で現状確認

// turbo
```pwsh
docker exec legalshield_postgres psql -U legalshield -d legalshield -c @"
SELECT
  (SELECT COUNT(*) FROM legalshield.problem_category)  AS categories,
  (SELECT COUNT(*) FROM legalshield.category_routing)  AS routes,
  (SELECT COUNT(*) FROM legalshield.support_org)       AS support_orgs,
  (SELECT COUNT(*) FROM legalshield.intake_session)    AS sessions;
"@
```

期待値（2026-05-26 時点）：
- categories: **12**
- routes: **71**
- support_orgs: **328+**（DV ingest 済みなら）
- sessions: 任意

## Step 5. 残課題から 1 つ in_progress にする

`docs/strategy/2026-05-26_dev_progress.md` の第 7 章「残課題」のリストから 1 つ選び、
ユーザーと相談してから着手する。
