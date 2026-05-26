# LegalShield / GIS Subsystem

> 日本法律救助 GIS 平台 — 整合公開資料庫 + 使用者 GPS → 即時回傳「離我最近的支援資源 + 該地區風險指標」

> **位置**: `d:\projects\LegalShield\gis\` — 本目錄是 LegalShield monorepo 的 **公開 GIS 子系統**。
> **關係**: 與既存 `../legalshield/backend/api.py`（私有 RAG/LLM, Windows GPU）並列獨立運行。
> **bridge**: `INTEGRATION.md` 説明兩個 backend 如何協作。

## Mission

ドメスティック・バイオレンス、性犯罪、ストーキング、企業の悪質行為などの被害者・サバイバーが、自分の現在地から **最も近い法律支援リソース**（法テラス・NPO・NGO・弁護士会）を **数秒以内** に取得し、同時に **その地域の犯罪リスク指標** を客観データで把握できる、無料の公益 GIS プラットフォーム。

LLM や個人化判例検索などの **重い・私有** な機能は `../legalshield/backend/api.py`
（Windows GPU + Ollama + LanceDB）が担当。本サブシステムは **軽量・公開・匿名** の
GIS 機能のみを担い、Docker で EC2 にも他環境にも独立配備可能。

## Architecture — 二段独立構成

```
┌────────────────────────────────────────────────────────────────────┐
│  EC2 (57.182.145.90, ap-northeast-1)  Ubuntu 22.04 LTS, Docker     │
│  /home/ubuntu/SylvaNexus_Platform/   (hiiforest, do not touch)     │
│  /home/ubuntu/LegalShield_jp/        (this repo)                   │
│                                                                     │
│  ┌──────────────────┐    ┌──────────────────┐                      │
│  │ hiiforest stack  │    │ legalshield stack │                      │
│  │ - frontend (8082)│    │ - api (8090)      │                      │
│  │ - backend (8002) │    │ - frontend (8092) │                      │
│  │ - gis-svc (8080) │    └──────────────────┘                      │
│  └──────────────────┘             │                                │
│           │                       │                                │
│           ▼                       ▼                                │
│  ┌──────────────────────────────────────────┐                      │
│  │ shared postgres (postgis/postgis:15-3.3) │                      │
│  │  - DB: SylvaNexus_Global  (hiiforest)    │                      │
│  │  - DB: legalshield        (this repo)    │                      │
│  └──────────────────────────────────────────┘                      │
│                                                                     │
│  nginx (host) → vhosts:                                            │
│   - hiiforest.com.conf      (existing)                             │
│   - legalshield.jp.conf     (NEW, in nginx/)                       │
└────────────────────────────────────────────────────────────────────┘
```

## Public data sources (all free, no API key)

| Category | Source | Format | Update |
|---|---|---|---|
| 犯罪統計 | 警察庁オープンデータ + e-Stat | CSV / JSON | 月次 |
| 法律相談所 | 法テラス 全国事務所一覧 | CSV | 不定期 |
| NPO 一覧 | 内閣府 NPO ホームページ | CSV (~80k) | 年次 |
| NGO 一覧 | 外務省 ODA NGO + JANIC | CSV / web | 年次 |
| 行政界 | 国土数値情報 N03 | Shapefile | 年次 |
| 人口統計 | e-Stat 国勢調査 | API + CSV | 5 年 |

## Quick start (local)

```powershell
# 1. clone
git clone https://github.com/Fuilko/LegalShield-jp.git
cd LegalShield-jp
copy .env.example .env

# 2. spin up own postgres + api + frontend
docker compose -f docker-compose.local.yml up -d --build

# 3. ingest sample data (法テラス + N03 行政界 first)
docker compose exec legalshield-api python -m ingest.run_all --datasets houterasu,n03

# 4. open
#    http://localhost:8092          (Leaflet front-end)
#    http://localhost:8090/docs     (FastAPI Swagger)
```

## Production deploy (shared EC2)

See `DEPLOYMENT.md`. TL;DR:
1. set GitHub secrets (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `EC2_INSTANCE_ID`)
2. `git push origin research` — GH Actions auto-deploys via SSM Run Command
3. on EC2 the first time, copy `nginx/legalshield.jp.conf` to `/etc/nginx/sites-enabled/` and reload

## API endpoints

```
GET  /api/v1/legalshield/nearest-support  ?lat&lng&radius_km&type
GET  /api/v1/legalshield/risk-score        ?lat&lng
POST /api/v1/legalshield/incident-report   {lat, lng, type, anonymous}
GET  /api/v1/legalshield/region-stats/{prefecture_code}
GET  /api/v1/legalshield/tiles/{z}/{x}/{y}.pbf
```

Full spec: `docs/API.md`. Swagger live at `/docs`.

## License

Code: Apache-2.0. Data: redistributed under each source's terms (mostly CC-BY 4.0 政府標準利用規約 v2.0).

## Status

- [x] scaffold complete
- [x] DB schema
- [x] 5 API endpoints (skeleton)
- [x] ingest pipelines (法テラス, N03, e-Stat crime)
- [x] Leaflet MVP front-end
- [x] GH Actions deploy.yml
- [ ] first end-to-end deploy (waiting on `EC2_INSTANCE_ID` secret)
- [ ] DNS / ACM cert for `legalshield.jp`
- [ ] real-data smoke test on production
