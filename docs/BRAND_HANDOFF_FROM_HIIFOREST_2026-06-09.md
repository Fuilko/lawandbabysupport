# LegalShield 品牌・前端交接包（來自 HiiForest 主站側）

> **From:** HiiForest (SylvaNexus) brand/UI session — 管 `hiiforest.com` 主站的一方
> **To:** LegalShield 專屬 agent（本 repo `lawandbabysupport` 或 internal repo）
> **Date:** 2026-06-09
> **與 `INFRA_HANDOFF_FROM_HIIFOREST_2026-06-09.md` 並列**，那份談基建，本份談品牌・對外定位・前端入口。
> **目的:** 讓新 conversation 不需回頭載入 SylvaNexus 那邊的 NAV / Hero / Sentry 對話歷史，省 token。

---

## 0. 為什麼有這份文件

2026-06-09 在 HiiForest 主站側，做了一輪「品牌軸回歸森林」的重整。LegalShield 從原本的 hub-and-spoke 三事業並列敘事，**降級為 HiiForest 衍伸的未來服務之一**（與 UAV/機械 Edge 並列），呈現在 `hiiforest.com` 的 Coming Soon 區塊。

決策有變動，需要明確告訴下一個接手 LegalShield 的 agent，避免：
- 又把 LegalShield 拉回 Hero 主舞台
- 沿用舊「弱者救援」字眼造成品牌不一致
- 把 hiiforest 主站當 LegalShield 的家而誤改 SaaSDocker repo

---

## 1. 邊界與所有權

| 項目 | 屬於誰 |
|---|---|
| `Fuilko/lawandbabysupport`（本 repo）| **你** = LegalShield agent |
| `Fuilko/legalshield-internal`（敏感 / NEVER cloud-AI）| **你**（但 cloud AI 不可讀其內部敏感資料）|
| `Fuilko/SaaSDocker`（HiiForest 主站）| HiiForest agent，**你不可改** |
| `hiiforest.com/landing/services-legalshield.html` | HiiForest agent 管，**你可請求調整**但不直接 push |
| 未來 `ls.hiiforest.com` | **你**（部署到自己的 nginx vhost）|
| iOS 原生 app `ios/LegalShield/` | **你** |

**規則**：跨 repo 改動 → 提 issue 或 mention HiiForest agent，不要 force-push 對方 repo。

---

## 2. 今日（2026-06-09）品牌決策摘要

### 2.1 定位調整

| 項目 | 舊（之前 hub-and-spoke）| 新（今日定案）|
|---|---|---|
| HiiForest 主站定位 | 三事業並列 | **森林專一** |
| LegalShield 在主站呈現 | Hero 並列「LegalShield」 | **#initiatives Coming Soon 卡片** |
| 對外描述用詞 | 「法律弱者救援」「弱勢」 | **「文書與資料整理的協助工具」** |
| 對 UAV/機械 | 「鑑定」「forensic」 | **「分析」「技術解析」**（Edge 服務）|
| 商業定位（敘事）| 三條獨立業務 | **「從智慧林業衍伸的服務」**（同一 GIS + LLM/SLM 底盤）|

### 2.2 通用敘事（可在 LegalShield 自己的對外文案沿用）

> 「同一套地理 + 時序資料技術底盤（PostGIS schema 共用），從森林經營出發，逐步延伸到實務工作的文書整理與資料協助。」

> 「資料以『位置 + 時序 + 內容』三軸統一管理。」

> 「所有事實主張必須附出處；無依據時明確標示『待專家確認』；不替代律師或專業諮詢。」

### 2.3 不寫的字眼（避免品牌不一致）

- ❌ 「弱者救援」「弱勢」(社會使命感太強，本服務是工具不是慈善)
- ❌ 「法律自救」(太誇張，可能踩法律邊界)
- ❌ 「免費律師」「自助訴訟」(誤導)
- ❌ 「鑑定」(指 forensics 那邊，避免跟司法鑑定混淆)

### 2.4 鼓勵的字眼

- ✅ 「協助工具」「アシスタント」「assistant tool」
- ✅ 「文書整理」「資料整理」「証拠保全」
- ✅ 「實務工作」「実務」
- ✅ 「待專家確認」「専門家確認待ち」（無 source 時）

---

## 3. 對外呈現入口（目前 / 未來）

### 目前（2026-06-09 起）

- 入口頁：`https://hiiforest.com/landing/services-legalshield.html`
  - 三語完整（zh-TW / ja-JP / en-US）
  - 內容：定位、技術能力（規劃中）、Roadmap、CTA
  - CTA：「來信洽詢」(mailto kenji@hiiforest.com) + 「夥伴登入」(→ `/landing/login_simple.html`)
  - 該頁 `<meta name="robots" content="noindex, nofollow">` → 暫不對 SEO 公開
- 在 `hiiforest.com` 主頁 `#initiatives` 區塊：第三張卡（橙色），標籤「開發中 · COMING」
- NAV 沒有 LegalShield 直接連結（保持主站專注森林）

### 未來上線（觸發條件：iOS app closed beta 啟動）

- 啟用 `ls.hiiforest.com`（DNS + wildcard cert + nginx server_name 分流）
- `hiiforest.com/landing/services-legalshield.html` 301 redirect → `https://ls.hiiforest.com/`
- 同時 hiiforest 主站 `#initiatives` LegalShield 卡片狀態徽章改「上線中 · LIVE」
- 詳見 `Fuilko/SaaSDocker:docs/SUBDOMAIN_PLAN_2026-06-09.md`

---

## 4. 占位頁可以參考、不要重複實作

**HiiForest 那邊已建好的占位頁** `frontend/landing/services-legalshield.html` 包含這些區塊（三語）：

1. Hero — `開發中 · IN DEVELOPMENT` badge
2. About — 「這是什麼？」(沿用 §2.2 敘事)
3. Capabilities (規劃中) — 證據保全 / 文書整理 / RAG 檢索接地 / 隱私優先
4. Roadmap — 2025 PoC / 2026 H1 (backend + iOS) / 2026 H2 (closed beta)
5. CTA — 來信 + 夥伴登入
6. Footer — `本頁為 LegalShield 開發中占位頁，實際服務上線時將遷移至 ls.hiiforest.com`

**你（LegalShield agent）的 ls.hiiforest.com 正式 landing 上線時**：
- 可以**沿用上述六區塊架構**保持品牌延續性
- 視覺要比占位頁更溫暖（針對一般民眾），但保留 Option B 配色系（off-white + forest green）
- iOS app 下載連結（App Store / TestFlight）替換占位頁的「夥伴登入」CTA

---

## 5. 對 hiiforest.com 主站 agent 的請求清單

未來要請 HiiForest agent 配合做的事（不要自己改 SaaSDocker repo）：

| 觸發 | 請求對方做什麼 |
|---|---|
| `ls.hiiforest.com` 啟用 | nginx vhost 加 301 redirect 規則（見 SUBDOMAIN_PLAN 第 4 階段） |
| LegalShield 從 Coming 變 LIVE | 主頁 `#initiatives` 第三張卡狀態徽章改色（橙→綠）、加「進入應用」CTA |
| iOS app 上 App Store | 主頁占位頁卡片加 App Store badge |
| 重大版本更新 | `AGENTS.md` §7.7 加註，避免後續 agent 把品牌位置改回 hub-and-spoke |

---

## 6. 既有的 LegalShield agent 規則仍適用（不可違反）

本文件**不取代** `AGENTS.md`（本 repo 根目錄）。那邊的規則持續有效：

- §2 接地絕對原則（RAG-First、L1-L7 harness、不替代專家）
- §3 隱私（去識別化、device-first）
- §4 開發統一性（PROGRESS.md 追記、ARCHITECTURE.md 不破壞）

本文件僅補充「對外品牌呈現」與「跨 HiiForest 主站的連結關係」。

---

## 7. 新 conversation 開頭 prompt 建議

```
任務：接續 LegalShield 開發（iOS / Web / 後端）
請先讀本 repo（lawandbabysupport）以下文件取得背景：
1. AGENTS.md（行為規範 + 反幻覺絕對原則）
2. ARCHITECTURE.md（主架構）
3. PROGRESS.md（最新進度，最上面那條）
4. docs/INFRA_HANDOFF_FROM_HIIFOREST_2026-06-09.md（基建層交接）
5. docs/BRAND_HANDOFF_FROM_HIIFOREST_2026-06-09.md（本文件 — 品牌/前端層交接）

完成後告訴我:
- 你看到的最新 PROGRESS 條目摘要
- 目前最迫切的開發任務是什麼

不要載 2026-06-09 SylvaNexus 那邊的 NAV / Hero / Sentry 對話歷史，那是 hub-and-spoke 撤銷的整理過程，跟你接下來的工作無關。
```

---

*記錄者：HiiForest 主站 session (Devin/Claude), 2026-06-09*
*Cross-ref: `Fuilko/SaaSDocker:docs/SUBDOMAIN_PLAN_2026-06-09.md`、`Fuilko/SaaSDocker:AGENTS.md §6.7`*
