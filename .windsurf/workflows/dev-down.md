---
description: LegalShield-jp 開発スタックを停止（データは保持）
---

# /dev-down — スタック停止（データ保持）

```pwsh
docker compose -f gis\docker-compose.local.yml down
```

> volume は残るので、次回 `dev-up` で ingest 済みデータがそのまま使える。
> 完全に消したい場合は `-v` を付けるが、消すと DV センター 328 件など再 ingest が必要。
