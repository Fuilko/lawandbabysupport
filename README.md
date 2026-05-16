# Law & Baby Support / LegalShield

> 🌐 **Language / 言語 / 語言**: [🇯🇵 日本語](#-日本語) · [🇺🇸 English](#-english) · [🇹🇼 繁體中文](#-繁體中文)
> 
> **Project Timeline →** [PROJECT_TIMELINE.md](./PROJECT_TIMELINE.md) (Past → Present → Future + Development Dates)

---

## 🇯🇵 日本語

**デジタル賦権（Digital Empowerment）** — AI 駆動の法律自救 + 婦幼医療補助プラットフォーム

### プロジェクト紹介

| App | 説明 | 対象 |
|-----|------|------|
| **LegalShield (法盾)** | 法律自救：証拠保全 → 戦略シミュレーション → 文書生成 → 専家紹介 | 被害者、本人訴訟者 |
| **PocketMidwife (口袋助産士)** | 婦幼医療：症状問診 → Edge AI 検傷 → Triage → 救急紹介 | 妊産婦、0-6歳児の親 |

### 技術的コア

- **証拠保全エンジン** — SHA256 + NTP タイムスタンプ + Audit Log
- **RAG 検索** — 法規・判例 / 医学ガイドライン、強制法源引用
- **SLM/LLM ルーティング** — プライバシー優先（ローカル SLM）、複雑案件はクラウド LLM、高リスクは人工
- **日本最大級法データベース** — 国法 623,000 件 + 判例 724,443 件（ベクトル化済み）

### 紹介ページ

- [🇯🇵 日本語版紹介](legalshield/docs/LEGALSHIELD_INTRO_JP.html)
- [🇹🇼 繁體中文版紹介](legalshield/docs/LEGALSHIELD_INTRO_ZH.html)
- [🇺🇸 English Version](legalshield/docs/LEGALSHIELD_INTRO_EN.html)
- [📑 統合版（三語切替）](legalshield/docs/LEGALSHIELD_INTRO_COMPREHENSIVE.html)

### 免責事項

- 本アプリは**補助ツール**であり、法律代理 / 医療診断ではありません
- すべての助言に法源または医学ガイドラインの出典を強制付記
- センシティブデータはローカル優先処理、サーバーは生データを保持しません

### 開発日付 NOTE

| 日付 | マイルストーン |
|------|--------------|
| 2026-05-04 | [PRODUCT_PLAN.md](./PRODUCT_PLAN.md) 作成 — 二本柱構想確立 |
| 2026-05-06 | POC v2~v3 — LanceDB 導入、71,054 件判例ベクトル化 |
| 2026-05-07 | POC v4 — RAG パイプライン稼働、Ollama 連携 |
| 2026-05-08~10 | 三語 HTML 紹介ページ作成 |
| 2026-05-11 | 開発者ストーリー刷新 — 「反乱宣言」叙事 |
| 2026-05-12~14 | Toyota Foundation 提案書・技術・予算精緻化 |

📋 **全タイムライン** → [PROJECT_TIMELINE.md](./PROJECT_TIMELINE.md)

---

## 🇺🇸 English

**Digital Empowerment** — AI-driven legal self-help + maternal/child healthcare assistance platform

### Project Overview

| App | Description | Target Users |
|-----|-------------|--------------|
| **LegalShield** | Legal self-help: evidence preservation → strategy simulation → document generation → expert referral | Victims, pro se litigants |
| **PocketMidwife** | Maternal/child healthcare: symptom triage → Edge AI assessment → emergency referral | Pregnant women, parents of 0-6 year olds |

### Technical Core

- **Evidence Vault Engine** — SHA256 + NTP timestamp + Audit Log
- **RAG Retrieval** — Laws & precedents / medical guidelines with forced source citation
- **SLM/LLM Router** — Privacy-first (local SLM), complex cases to cloud LLM, high-risk to human
- **Japan's Largest Legal Database** — 623,000 national laws + 724,443 precedents (vectorized)

### Intro Pages

- [🇯🇵 Japanese](legalshield/docs/LEGALSHIELD_INTRO_JP.html)
- [🇹🇼 Traditional Chinese](legalshield/docs/LEGALSHIELD_INTRO_ZH.html)
- [🇺🇸 English Version](legalshield/docs/LEGALSHIELD_INTRO_EN.html)
- [📑 Comprehensive (Trilingual Switch)](legalshield/docs/LEGALSHIELD_INTRO_COMPREHENSIVE.html)

### Disclaimer

- This app is an **auxiliary tool**, not legal representation / medical diagnosis
- All advice includes mandatory legal/medical source citations
- Sensitive data is processed locally first; servers do not hold raw data

### Development Dates

| Date | Milestone |
|------|-----------|
| 2026-05-04 | [PRODUCT_PLAN.md](./PRODUCT_PLAN.md) created — dual-track concept established |
| 2026-05-06 | POC v2~v3 — LanceDB adoption, 71,054 precedents vectorized |
| 2026-05-07 | POC v4 — RAG pipeline operational, Ollama integration |
| 2026-05-08~10 | Trilingual HTML intro pages created |
| 2026-05-11 | Developer story revamp — "Declaration of Uprising" narrative |
| 2026-05-12~14 | Toyota Foundation proposal, technical & budget refinement |

📋 **Full Timeline** → [PROJECT_TIMELINE.md](./PROJECT_TIMELINE.md)

---

## 🇹🇼 繁體中文

**數位賦權（Digital Empowerment）** — AI 驅動的法律自救 + 婦幼醫療輔助平台

### 專案介紹

| App | 說明 | 對象 |
|-----|------|------|
| **LegalShield (法盾)** | 法律自救：證據保全 → 策略模擬 → 文書生成 → 律師轉介 | 本人訴訟者、被害者 |
| **PocketMidwife (口袋助產士)** | 婦幼醫療：症狀問卷 → Edge AI 檢傷 → Triage → 急診轉介 | 偏鄉父母、孕產婦 |

### 技術核心

- **存證引擎** — SHA256 + NTP 時間戳 + Audit Log
- **RAG 檢索** — 法規判例 / 醫學指引，強制引用出處
- **SLM/LLM 路由** — 隱私優先（本地 SLM），超限接雲端 LLM，高風險轉人工
- **日本最大級法資料庫** — 國法 623,000 件 + 判例 724,443 件（已向量化）

### 介紹頁面

- [🇯🇵 日本語版介紹](legalshield/docs/LEGALSHIELD_INTRO_JP.html)
- [🇹🇼 繁體中文版介紹](legalshield/docs/LEGALSHIELD_INTRO_ZH.html)
- [🇺🇸 English Version](legalshield/docs/LEGALSHIELD_INTRO_EN.html)
- [📑 統合版（三語切換）](legalshield/docs/LEGALSHIELD_INTRO_COMPREHENSIVE.html)

### 免責設計

- App = 輔助工具，**非**法律代理 / **非**醫療診斷
- 所有建議強制附帶法源或醫學指南出處
- 敏感資料優先本地處理，伺服器不持有原始資料

### 開發日期 NOTE

| 日期 | 里程碑 |
|------|--------|
| 2026-05-04 | [PRODUCT_PLAN.md](./PRODUCT_PLAN.md) 作成 — 二本柱構想確立 |
| 2026-05-06 | POC v2~v3 — LanceDB 導入、71,054 件判例向量化 |
| 2026-05-07 | POC v4 — RAG 管道運作、Ollama 連動 |
| 2026-05-08~10 | 三語 HTML 介紹頁面製作 |
| 2026-05-11 | 開發者故事翻新 — 「反亂宣言」敘事 |
| 2026-05-12~14 | Toyota Foundation 提案書、技術・預算精緻化 |

📋 **完整時間線** → [PROJECT_TIMELINE.md](./PROJECT_TIMELINE.md)

---

## 📂 Directory Structure

```
lawandbabysupport/
├── README.md                    ← This file (trilingual)
├── PROJECT_TIMELINE.md          ← Past → Present → Future + dates
├── LICENSE                      ← MIT License
├── PRODUCT_PLAN.md              ← Product planning
├── CASE_VERDICT_AND_APP_DESIGN.md
├── MARKET_ANALYSIS.md
├── PORTFOLIO_COMPARISON.md
├── shared/                      ← Shared core (evidence + RAG + router)
├── legalshield/                 ← LegalShield App
│   ├── backend/                 ← Python backend (FastAPI + Ollama + LanceDB)
│   ├── crawlers/                ← e-Gov law / precedent / statistics crawlers
│   ├── docs/                    ← Intro pages, ONE_PAGER, UX specs
│   ├── frontend/                ← Streamlit demo / Flutter (future)
│   ├── agents/                  ← AI agent system
│   └── knowledge/               ← Data (gitignored, regeneratable via scripts)
├── pocketmidwife/               ← PocketMidwife App (future)
└── tests/
```

### クイックスタート / Quick Start / 快速開始

```powershell
# Windows (PowerShell)
cd D:\projects\LegalShield
.\.venv\Scripts\Activate.ps1

# RAG 検索（最速 phi4:14b）
python legalshield\backend\rag_query.py -m phi4:14b -k 6 "質問文"

# インタラクティブモード
python legalshield\backend\rag_query.py -i -m phi4:14b

# 検索のみ（LLM スキップ・最速）
python legalshield\backend\rag_query.py --retrieve-only "質問文"
```

> **Note**: Knowledge data (`lancedb/`, `knowledge/*.parquet`, `knowledge/raw/`) is excluded from git. Regenerate via `crawlers/` + `backend/` scripts. See `legalshield/knowledge/README.md`.

---

## 📜 License

[MIT License](./LICENSE) — © 2026 劉建志 (Kenji Liu) / 光伊フォレスト株式会社

> 本ソフトウェアは法律・医療アドバイスを提供するものではありません。
> This software does not provide legal or medical advice.

---

*Last updated: 2026-05-14*
