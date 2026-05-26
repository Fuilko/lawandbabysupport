# GIS Subsystem Integration Guide

How `gis/` (this directory) bridges to the rest of the LegalShield monorepo.

```
d:\projects\LegalShield\
├── legalshield/                    ← 私有・重い・GPU が必要
│   ├── backend/api.py              ← FastAPI on Windows :8000 (Tailscale)
│   │                                  - LLM (Ollama gemma3:27b)
│   │                                  - RAG over LanceDB (precedents + statutes)
│   │                                  - sentence-transformers / CUDA
│   │   別 endpoints:
│   │   POST /rag/query, /rag/retrieve, /rag/statutes, /rag/partners
│   │   POST /api/generate, /api/chat (Ollama proxy)
│   ├── lancedb/                    ← 判例 + 法令 vectors (DuckDB + LanceDB)
│   └── frontend/streamlit_demo.py
│
├── ios/LegalShield/                ← Swift app
│   └── 既存: JapaneseLegalRAG.swift → legalshield/backend (private)
│   └── NEW (to add): GISService.swift → gis/services/legalshield-api (public)
│
├── gis/                            ← THIS — 公開・軽量・無 LLM
│   ├── services/legalshield-api/   FastAPI on Docker :8080
│   │   GET  /api/v1/legalshield/nearest-support
│   │   GET  /api/v1/legalshield/risk-score
│   │   POST /api/v1/legalshield/incident-report
│   │   GET  /api/v1/legalshield/region-stats/{prefecture_code}
│   │   GET  /api/v1/legalshield/tiles/{z}/{x}/{y}.pbf
│   ├── ingest/                     公開データ ETL → PostGIS
│   ├── frontend/                   Leaflet MVP (legalshield.jp)
│   └── docker-compose.local.yml
│
└── (SaaSDocker は別ディレクトリ・別レポ・触らない)
```

## なぜ二段構成か

| 観点 | `legalshield/backend/api.py` (private) | `gis/services/legalshield-api` (public) |
|---|---|---|
| 公開度 | Tailscale 内部のみ | 公開 web (legalshield.jp) |
| 認証 | iOS app 専用 (将来 JWT) | 匿名 OK (incident report 含む) |
| 計算負荷 | 重 (LLM + embedding) | 軽 (PostGIS query) |
| ハードウェア | Windows + RTX 4080 (CUDA) | 任意の Docker host (EC2 t4g.small で十分) |
| データ | LanceDB / DuckDB (判例 + 法令) | PostgreSQL + PostGIS (位置情報) |
| 障害時の影響 | iOS app 個人化機能停止 | web 公開窓口停止 |
| 個人情報 | 持つ可能性あり (会員登録時) | 持たない (geom は obfuscate 済) |

**この分離が重要な理由**:
1. **Privacy by architecture**: 公開 web に個人情報・LLM・RAG を一切置かない
2. **Cost**: GPU 不要なので EC2 は最小構成 (¥1,500/月)
3. **Resilience**: GPU マシンが落ちても公開 web は動き続ける
4. **Compliance**: 公開部分のみ open source 化しても私有モデル/データは漏れない

## Bridge — 二者間の連携パターン

### Pattern 1: 共有 PostgreSQL (推奨, MVP)

両 backend が **同じ PostgreSQL** を参照（別 DB or 別 schema）:

```
┌─ Windows: legalshield.backend.api ─┐
│  reads:  legalshield.support_org   │  ← 法テラス・NPO 一覧 (gis が ingest)
│  writes: -                         │
└────────────────────────────────────┘
                ↕ network
┌─ EC2 Docker: gis api ──────────────┐
│  reads/writes: legalshield.*       │  ← 全責任
└────────────────────────────────────┘
```

設定:
- gis/.env の `DATABASE_URL` = EC2 上の PostGIS
- legalshield/backend/api.py に新環境変数 `LEGALSHIELD_PG_URL` を追加し、
  必要時のみ Tailscale 経由で同 DB に接続

利点: 単一 source of truth、データ重複なし
注意: Tailscale 経由読取は遅い → backend 側はキャッシュ層を挟む

### Pattern 2: 一方向 export (シンプル, 後発)

gis 側が定期的に CSV / Parquet を S3 に書き出し、Windows backend が取り込む。
Tailscale 接続不要、双方完全独立。

## iOS app からの利用

`ios/LegalShield/LegalShield/` に `GISService.swift` を追加（未着手）:

```swift
// Pseudo-code
struct GISService {
    static let baseURL = "https://legalshield.jp/api/v1/legalshield"

    static func nearestSupport(lat: Double, lng: Double) async throws -> [SupportOrg] { ... }
    static func riskScore(lat: Double, lng: Double) async throws -> RiskScore { ... }
    static func reportIncident(lat: Double, lng: Double, type: String, description: String?) async throws { ... }
}
```

既存の `JapaneseLegalRAG.swift`（private RAG）と並列に存在。
重い質問 → JapaneseLegalRAG。地理クエリ → GISService。両者を組み合わせるのは UI 層の責任。

## ingest data 共有

`gis/ingest/` が読み込む生データは `data_set/` に配置可能:

```
d:\projects\LegalShield\
├── data_set/             ← 既存: 法律生コーパス置き場
│   ├── law/
│   ├── precedent/
│   └── (NEW) gis/
│       ├── N03/                    国土数値情報
│       ├── houterasu/              法テラス CSV
│       └── crime/                  e-Stat 犯罪統計
└── gis/ingest/run_all.py
    -> reads from ../data_set/gis/* if DATA_ROOT 環境変数で指定
```

## SaaSDocker / hiiforest との関係

**完全に独立** (Forest 系の SylvaNexus と本プラットフォームは無関係)。
偶然 EC2 を共用する選択肢があっただけで、必須ではない。
本サブシステムは単独 docker-compose で完結 — どこにでも配備可能。

## ロードマップ

- [x] gis/ scaffolding (5 endpoints + Leaflet front-end + ingest pipelines)
- [x] Docker stack (postgres + api + frontend)
- [ ] GISService.swift を ios/LegalShield に追加
- [ ] data_set/gis/ に公開データを置く
- [ ] 共有 postgres pattern (Tailscale 経由) を選ぶか、export pattern を選ぶか確定
- [ ] 公開ドメイン (legalshield.jp など) 取得 + ACM/LE TLS
- [ ] 初回 EC2 deploy (DEPLOYMENT.md §2 の手順)
