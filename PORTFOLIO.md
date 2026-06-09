# HIIFOREST Portfolio Index

> **Top-level entry point for any AI agent working under `D:\projects\*` or `D:\DSylvaNexus_Workspace\*`**
>
> 任何 AI agent 進入此處任一子目錄前，必須先讀本文件，再讀各專案的 `AGENTS.md`。
>
> いずれの AI エージェントも、本ファイルを最初に読み、その後に各プロジェクトの `AGENTS.md` を読むこと。

**Last updated**: 2026-06-09

---

## 0. Owner & Entity

| 項目 | 内容 |
|---|---|
| **会社** | HIIFOREST LTD（合同会社） |
| **代表** | 劉建志 (LIU CHIEN CHIH) — 永住者 |
| **ドメイン** | hiiforest.com |
| **ミッション** | GIS + AI を用いて、林業・法律・医療・機械事故鑑定の各領域における専門家アクセスを民主化する |

---

## 1. Three Product Lines (DO NOT MERGE CODEBASES)

| ID | Project | Path | GitHub | Branch | Status |
|---|---|---|---|---|---|
| **①** | **SylvaNexus / HiiForest** | `D:\DSylvaNexus_Workspace\SylvaNexus_Platform` | `Fuilko/SaaSDocker` (private) | `research` | live (https://hiiforest.com) |
| **②a** | **LegalShield + PocketMidwife** (technical OSS) | `D:\projects\LegalShield` | `Fuilko/lawandbabysupport` (**PUBLIC**) | `main` | active dev — NLnet target |
| **②b** | **LegalShield Internal** (commercial / legal / personal) | `D:\projects\legalshield-internal` | `Fuilko/legalshield-internal` (private) | `main` | 🔴 **NEVER cloud-AI** — see its `AGENTS.md` |
| **③a** | **HII Forensics — Toolkit** | `D:\projects\hii-forensics-toolkit` | `Fuilko/hii-forensics-toolkit` (private) | `main` | skeleton (docs only, source code TBD) |
| **③b** | **HII Forensics — Cases** | `D:\projects\flylog_analysis` | (LOCAL ONLY, NEVER push) | — | active case (Mapry M4-0 ADR ongoing — **DO NOT publicize**) |

### Domain summary

- **①** 森林経営 SaaS — 衛星 + UAV SfM + iPhone LiDAR + GEDI/ETH Canopy Height
- **②** 法律弱者・婦幼医療弱者 救援 — 623K 法令 + 724K 判例 RAG + L1–L7 anti-hallucination harness
  - **②a** = OSS technical core (de-identified, NLnet-friendly)
  - **②b** = commercial strategy + active legal cases (cloud-AI BANNED)
- **③** UAV / 機械事故 第三者技術解析 — ext4 forensic + ROS2 / ArduPilot / MAVROS log → 多言語報告書
  - **③a** = vendor-agnostic toolkit (private, no case data)
  - **③b** = active case storage (LOCAL ONLY, never on git)

---

## 2. Sister Directories under `D:\projects\`

| Folder | Purpose | Relation |
|---|---|---|
| `_ref_SaaSDocker` | Archive of older SylvaNexus snapshot | reference only, do not edit |
| `file_maker` | TBD — purpose not yet documented | unclassified |
| `open-evidence-privacy-toolkit` | Evidence de-identification library | shared by ② and ③ |

---

## 3. Shared Technical Foundation (Concepts, Not Code)

| Layer | Pattern | Canonical Implementation |
|---|---|---|
| **GIS** | PostGIS + Leaflet/MapLibre | ① `services/gis-service/` |
| **Anti-hallucination** | L1–L7 harness | ② `legalshield/backend/harness.py` |
| **Privacy / 去識別化** | LocationAnonymizer + Laplace DP | `open-evidence-privacy-toolkit` |
| **Multi-language report** | Jinja2 + WeasyPrint, zh-TW / ja / en | each project has fragments |
| **iOS shells** | SwiftUI + offline-first + Core Data | ① `apps/ios/` + ② `ios/LegalShield/` |
| **Auth** | FastAPI JWT + bcrypt | ① `backend/app/auth/` |
| **LLM access** | Provider-abstracted (`LLMProvider`) | ② `legalshield/backend/` |
| **Forensic extraction** | ext4 image + ROS bag + DataFlash | ③ `flylog_analysis/` scripts |

> **Rule**: When project X needs functionality already implemented in project Y → **redirect (HTTP API or doc reference), do NOT reimplement**.

---

## 4. Cross-Project Rules for AI Agents

1. **NEVER suggest merging codebases.** They share concepts, not code.
2. **Read project-level `AGENTS.md` AFTER this file.** This file is portfolio context; project AGENTS.md is execution context.
3. **Cross-domain feature requests** → redirect, don't reimplement:
   - 「LLM 法律回答」 → ②a `/rag/answer` (harness.py L1–L7)
   - 「無人機 log 解析」 → ③a `hii-forensics-toolkit`
   - 「林業 GIS 計算」 → ① `gis-service` endpoints
   - 「証拠去識別化」 → `open-evidence-privacy-toolkit`
4. **Independent databases.** Each project has its own PostgreSQL instance. NEVER share connections.
5. **Cross-repo communication is HTTP API only.** Never `import` across project boundaries.
6. **Active forensic case (Mapry M4-0)**: MUST NOT be discussed publicly until ADR resolved. Capability descriptions on website MUST be anonymized.
7. **Bus factor = 1.** Maintain documentation rigorously. Each project's `PROGRESS.md` (or equivalent) updated after meaningful changes.
8. **Anti-hallucination is non-negotiable.** Any LLM-generated factual claim (legal, medical, scientific) MUST go through harness retrieval gate. No exceptions.
9. **Cloud AI processing of ②b and ③b is FORBIDDEN.** See those repos' AGENTS.md. Use local Ollama or de-identification scripts only.

---

## 5. Cross-Business Synergy Opportunities (Real Revenue Paths)

| Trigger | Cross-line flow | Est. revenue / case |
|---|---|---|
| 林業客戶 UAV 墜機 | ① customer → ③ forensic → ② ADR support | ¥3M – ¥10M |
| 森林所有權 境界争い | ① forest map + ② legal RAG + 弁護士紹介 | ¥500K – ¥2M |
| J-Credit MRV 監査対応 | ① 客觀資料 + ② 法律支援 | recurring |
| 産婦救急 / 位置プライバシー | ② PocketMidwife + privacy-toolkit | per platform contract |
| 製造物責任訴訟 | ③ technical analysis + ② legal proceedings | ¥1M – ¥5M |

---

## 6. Active Compliance / Business Status (2026-06)

- **HIIFOREST 合同会社**: 設立済み, 永住者代表
- **適格請求書発行事業者 (T番号)**: 申請状況確認要
- **個情法対応 PMS**: ② に基本実装あり、①③ への展開要
- **Pマーク**: 未取得（B2B 大企業 / 自治体向けに優先取得検討）
- **IT導入支援事業者登録**: 未申請（次年度 2027-Q1 想定）
- **JFC 創業融資**: 未申請
- **ものづくり補助金 / 事業再構築補助金**: ③ 設備購入で申請計画
- **PL 保険 / サイバー保険**: ③ サービス開始前に加保必要

---

## 7. Where to Find What

| Need | Look here |
|---|---|
| ① architecture audit | `SylvaNexus_Platform/docs/ARCHITECTURE_AUDIT_2026-06-09.md` |
| ① roadmap | `SylvaNexus_Platform/docs/ROADMAP.md` |
| ① system integration | `SylvaNexus_Platform/docs/SYSTEM_INTEGRATION_ROADMAP.md` |
| ② architecture | `LegalShield/ARCHITECTURE.md` |
| ② progress (most recent) | `LegalShield/PROGRESS.md` |
| ② harness L1–L7 | `LegalShield/legalshield/backend/harness.py` |
| ② grants 申請資料 | `LegalShield/docs/grants/` |
| ③ Mapry case (confidential) | `flylog_analysis/evidence/README.md` |
| ③ 取得層・分析層 設計 | (to be documented in `flylog_analysis/docs/`) |
| Cross-line strategy | this file |

---

## 8. Customer Mix & GTM Channels

| Customer type | Primary product | Sales flow | Subsidy applicable? |
|---|---|---|---|
| 大型企業 ESG (TSMC, 製紙等) | ① + ③ | Direct B2B vendor onboarding | ❌ |
| 林業会社 (中小) | ① + ②(境界争い) + ③(墜機) | B2B + IT 導入補助金 | ✅ |
| 森林組合 | ① | B2B + IT 導入補助金 | ✅ |
| 地方自治体 | ① + ② | 政府調達 / 入札 | ❌ (要 入札参加資格) |
| 個人 (DV / 法律弱者) | ② | App Store / 自費 / 助成 | ✅ (NLnet, 公益財団) |
| 損害保険会社 | ③ | 直接 B2B | ❌ |
| 弁護士事務所 | ② + ③ | 紹介 / API 連携 | ❌ |

---

## 9. Risk Register (Top 5)

| Risk | Severity | Mitigation |
|---|---|---|
| Bus factor = 1 | CRITICAL | Documentation > tribal knowledge; Devin/Cascade/Claude redundancy |
| ① no DB backup (6+ weeks) | CRITICAL | EBS snapshot + pg_dump (in progress) |
| ③ Active ADR case publicization risk | HIGH | Anonymize all public mentions until resolved |
| Cross-project agent confusion | HIGH | This PORTFOLIO.md + per-project AGENTS.md |
| Compliance gap blocks B2B sales | HIGH | T番号 → Pマーク 6 month track |

---

*Maintained by 劉建志 + AI agents (Cascade / Claude Code / Cursor / Devin CLI / Codex).*
*This file is the single source of truth for portfolio-level context.*
*If outdated, the most recent project-level `PROGRESS.md` takes precedence.*
