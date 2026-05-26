---
description: LegalShield-jp 日常開発スタートアップ（既にセットアップ済みのマシン用）
---

# /dev-up — 開発スタックを起動

`setup-new-machine` 後、日々の開発開始時に使う。

// turbo
```pwsh
docker compose -f gis\docker-compose.local.yml up -d
Start-Sleep -Seconds 3
docker compose -f gis\docker-compose.local.yml ps
```

ヘルスチェック：

// turbo
```pwsh
try { Invoke-RestMethod http://localhost:8090/health; "API OK" } catch { "API not ready yet" }
```

ブラウザを開く：

// turbo
```pwsh
Start-Process http://localhost:8092
```
