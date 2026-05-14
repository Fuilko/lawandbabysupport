# 法律 AI 開源資源地圖

> 調查日期：2026-05-05 | 目標：建立公用版法律 AI 助手所需的所有 GitHub 開源資源

---

## 一、立即可用的工具 (本週就能跑)

### 1.1 日本法令資料庫 + MCP Server

| 專案 | 說明 | 用途 |
|------|------|------|
| [e-Gov 法令 API v2](https://laws.e-gov.go.jp/api/2/swagger-ui) | **日本政府官方** 法令檢索 API，JSON/XML 格式 | 搜尋民法、製造物責任法 (PL 法)、航空法、消費者契約法 |
| [ryoooo/e-gov-law-mcp](https://lobehub.com/mcp/ryoooo-e-gov-law-mcp) | **MCP Server** 直接串接 e-Gov API → Claude/Ollama 可用 | 讓 AI 直接引用法條原文，防止幻覺 |
| [kentaroajisaka/tax-law-mcp](https://github.com/kentaroajisaka/tax-law-mcp) | 稅法 MCP Server (e-Gov + 國稅庁) | 架構參考，可 fork 改成 PL 法/航空法專用 |
| [kentaroajisaka/labor-law-mcp](https://github.com/kentaroajisaka/labor-law-mcp) | 勞動法 MCP Server (e-Gov + 厚勞省) | 架構參考 |
| [riywo/law.e-gov.go.jp](https://github.com/riywo/law.e-gov.go.jp) | 日本法令爬蟲 (全量下載) | 離線法令資料庫 |

### 1.2 日本判例資料庫

| 專案 | 說明 | 用途 |
|------|------|------|
| [japanese-law-analysis/listup_precedent](https://github.com/japanese-law-analysis/listup_precedent) | **裁判所** 判例爬蟲 (裁判所 HP 全量爬取) | 搜尋 PL 法判例、製品欠陥判例 |
| [japanese-law-analysis/data_set](https://github.com/japanese-law-analysis/data_set) | 已爬取的判例文字檔 (可直接用) | RAG 向量化 → 判例檢索 |
| [japanese-law-analysis/listup_law](https://github.com/japanese-law-analysis) | e-Gov 法令 XML 批量下載解析 | 法令全文離線資料庫 |
| [裁判所判例検索](https://www.courts.go.jp/app/hanrei_jp/search1) | 官方搜尋介面 | 手動搜尋 PL 法判例 |
| [lawqa_jp](https://github.com/taishi-i/awesome-japanese-nlp-resources) | 日本法令多選式 QA 資料集 | 微調 SLM 用 |

### 1.3 本地 RAG 平台 (你已經有 Open WebUI + Ollama)

| 專案 | Stars | 說明 | 用途 |
|------|-------|------|------|
| [Mintplex-Labs/anything-llm](https://github.com/Mintplex-Labs/anything-llm) | 53K+ | **全功能 RAG 平台**: PDF/文件→向量化→聊天, 支援 Ollama | 上傳判例 PDF + 法條 → 即時對話 |
| [open-webui/open-webui](https://github.com/open-webui/open-webui) | 100K+ | **你已經在跑的** AI 介面, 內建 RAG | 直接上傳法律文件建知識庫 |
| [harvard-lil/olaw](https://github.com/harvard-lil/olaw) | 哈佛法學院 | **法律專用 RAG 工作台**: Tool-based RAG + 法院 API | 法律 AI 研究基礎 |
| [jashankish/local-legal-ai](https://github.com/jashankish/local-legal-ai) | — | **完全本地**法律 AI: 無需外部 API, 向量搜尋 | 隱私優先的法律助手 |

---

## 二、法律 AI 助手框架

### 2.1 法律專用 AI

| 專案 | 說明 | 適用 |
|------|------|------|
| [lawglance/lawglance](https://github.com/lawglance/lawglance) | 開源 RAG 法律助手: 多語言、語音輸入 | 公用版法律助手基礎 |
| [AbhaySingh71/AI-Lawyer-RAG-with-Deepseek](https://github.com/AbhaySingh71/AI-Lawyer-RAG-with-Deepseek) | DeepSeek R1 + Ollama 法律 RAG | 本地推理 + 法律推理 |
| [lixx21/legal-document-assistant](https://github.com/lixx21/legal-document-assistant) | RAG 法律文件分析 | 合約/文書分析 |

### 2.2 Awesome Lists (資源索引)

| 專案 | 說明 |
|------|------|
| [Vaquill-AI/awesome-legaltech](https://github.com/Vaquill-AI/awesome-legaltech) | **LegalTech 完整清單**: 法律 AI 模型、Embedding、資料集、工具 |
| [maastrichtlawtech/awesome-legal-nlp](https://github.com/maastrichtlawtech/awesome-legal-nlp) | **法律 NLP 論文清單**: 180+ 篇, 2024-2025 最新 |
| [openlegaldata/awesome-legal-data](https://github.com/openlegaldata/awesome-legal-data) | **法律開放資料集**: 全球判例/法令資料集 |
| [taishi-i/awesome-japanese-nlp-resources](https://github.com/taishi-i/awesome-japanese-nlp-resources) | **日文 NLP 資源**: 含法律資料集、判例工具 |

---

## 三、大陪審團 / 多 Agent 模擬對抗

### 3.1 Multi-Agent 辯論框架

| 專案 | Stars | 說明 | 你的用途 |
|------|-------|------|---------|
| [Skytliang/Multi-Agents-Debate](https://github.com/Skytliang/Multi-Agents-Debate) | — | **MAD 框架**: 多 Agent 辯論提升推理品質 | 原告 vs 被告 vs 法官模擬 |
| [iason-solomos/Deb8flow](https://github.com/iason-solomos/Deb8flow) | — | **LangGraph 辯論系統**: 動態路由 + 事實驗證 + 仲裁 | 法律攻防模擬 |
| [thunlp/ChatEval](https://github.com/thunlp/ChatEval) | — | **多角色辯論評估**: LLM 扮演不同角色自主辯論 | 模擬法官/對方律師 |
| [databricks/judges](https://github.com/quotient-ai/judges) | — | **LLM 陪審團**: 多模型投票評估 | 用多個 LLM 模擬陪審團決議 |

### 3.2 Multi-Agent 開發框架

| 專案 | Stars | 說明 | 適合度 |
|------|-------|------|--------|
| [crewAIInc/crewAI](https://github.com/crewaiinc/crewai) | 25K+ | **角色扮演多 Agent 框架**: 定義角色→任務→協作 | ⭐ 最推薦 — 簡單、快、適合 SMB |
| [microsoft/autogen](https://github.com/microsoft/autogen) | 40K+ | **微軟多 Agent 框架**: 複雜協作、審計追蹤 | 企業級，稍重 |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 10K+ | **狀態圖 Agent 框架**: 精確控制流程 | 複雜法律工作流 |

### 3.3 大陪審團模擬：具體架構

```
用 CrewAI 定義 5 個 Agent:

1. 📋 案情整理官 (Case Analyst)
   - 讀取你的證據 → 產出結構化案情摘要
   
2. ⚖️ 原告律師 (Plaintiff Attorney)
   - 用 PL 法 + 民法 → 建構攻擊論點

3. 🛡️ 被告律師 (Defense Attorney)  
   - 找出你論點的弱點 + 模擬對方反駁

4. 👨‍⚖️ 法官 (Judge)
   - 評估雙方論點 + 引用判例 + 預判勝率

5. 📝 書記官 (Court Clerk)
   - 把結果整理成可提出的法律文書
```

---

## 四、文件閱讀 / PDF 分析

| 專案 | 說明 | 用途 |
|------|------|------|
| [opendataloader-project/opendataloader-pdf](https://github.com/opendataloader-project/opendataloader-pdf) | PDF → 結構化 Markdown (表格、公式、圖表) | 判例 PDF → RAG 可用格式 |
| [sepinf-inc/IPED](https://github.com/sepinf-inc/IPED) | **數位鑑識工具** (巴西聯邦警察開發) | 證據分析 (你的 SD 卡鑑識已用類似方法) |
| [huridocs/pdf-document-layout-analysis](https://github.com/huridocs/pdf-document-layout-analysis) | PDF 版面分析 AI (人權文件專用) | 法律文件結構化 |

---

## 五、推薦立即行動方案

### Phase 0: 今晚 (30 分鐘)

```bash
# 1. 在你已有的 Open WebUI 上建一個「法律」知識庫
#    上傳：ADR 申立書、鑑定報告、法條 PDF
#    → 立刻可以對話式查詢你的案件資料

# 2. 安裝 e-Gov 法令 MCP Server
git clone https://github.com/ryoooo/e-gov-law-mcp.git
cd e-gov-law-mcp && npm install && npm run build
# → Windsurf/Claude 可直接查日本法條
```

### Phase 1: 本週 (ADR + 訴狀準備)

```bash
# 1. 下載判例資料庫
git clone https://github.com/japanese-law-analysis/listup_precedent.git
git clone https://github.com/japanese-law-analysis/data_set.git
# → 搜尋 PL 法 (製造物責任法) 相關判例

# 2. 安裝 AnythingLLM (更強的 RAG)
docker pull mintplexlabs/anythingllm
docker run -d -p 3001:3001 \
  --add-host=host.docker.internal:host-gateway \
  -v anything-llm-storage:/app/server/storage \
  mintplexlabs/anythingllm
# → 建立「Mapry 案件」工作空間，上傳全部證據+法條+判例

# 3. 安裝 CrewAI (大陪審團模擬)
pip install crewai crewai-tools
# → 定義 5 Agent 對你的案件做攻防模擬
```

### Phase 2: 下週起 (公用版開發)

```bash
# 1. Fork lawglance 改成日本法律專用
git clone https://github.com/lawglance/lawglance.git

# 2. 整合 e-Gov MCP + 判例 RAG + CrewAI
# → 公用版 LegalShield 雛形
```

---

## 六、關鍵法條速查 (你的案件)

以下是你的 Mapry 案件可能用到的法條，可透過 e-Gov API 取全文：

| 法條 | 內容 | 適用 |
|------|------|------|
| **製造物責任法 (PL法)** 第3條 | 製造者對產品缺陷造成的損害負賠償責任 | ⭐ 核心：無人機缺陷 |
| **PL法** 第2條2項 | 「缺陷」定義：欠缺通常應有的安全性 | 18 項安全缺陷 |
| **民法** 第562-564條 | 契約不適合 (瑕疵擔保) | 代金返還請求 |
| **民法** 第415條 | 債務不履行的損害賠償 | 損害賠償 |
| **民法** 第709條 | 不法行為的損害賠償 | 車輛損害、出張費用 |
| **消費者契約法** 第4條 | 不當勸誘・重要事實不告知 | 隱瞞缺陷出貨 |
| **航空法** 第132條之85 | 無人機飛行安全基準 | 安全裝置欠缺 |
| **下請法** | 中小企業保護 (下請代金遲延等) | ADR 申立根據 |

---

## 七、GitHub 資源一覽表 (可直接 clone)

### 今晚就 clone

```bash
# === 法令 + 判例資料 ===
git clone https://github.com/japanese-law-analysis/listup_precedent.git
git clone https://github.com/japanese-law-analysis/data_set.git
git clone https://github.com/riywo/law.e-gov.go.jp.git

# === MCP Server (AI 直接查法條) ===
git clone https://github.com/ryoooo/e-gov-law-mcp.git
git clone https://github.com/kentaroajisaka/tax-law-mcp.git
git clone https://github.com/kentaroajisaka/labor-law-mcp.git

# === 法律 AI 助手 ===
git clone https://github.com/lawglance/lawglance.git
git clone https://github.com/AbhaySingh71/AI-Lawyer-RAG-with-Deepseek.git
git clone https://github.com/harvard-lil/olaw.git
git clone https://github.com/jashankish/local-legal-ai.git

# === 多 Agent 辯論 (大陪審團) ===
git clone https://github.com/Skytliang/Multi-Agents-Debate.git
git clone https://github.com/iason-solomos/Deb8flow.git
git clone https://github.com/thunlp/ChatEval.git

# === RAG 平台 ===
git clone https://github.com/Mintplex-Labs/anything-llm.git

# === Awesome Lists (參考) ===
git clone https://github.com/Vaquill-AI/awesome-legaltech.git
git clone https://github.com/maastrichtlawtech/awesome-legal-nlp.git
git clone https://github.com/openlegaldata/awesome-legal-data.git

# === 文件分析 ===
git clone https://github.com/opendataloader-project/opendataloader-pdf.git
```

### 優先序

```
1. e-gov-law-mcp          → 今晚裝好，AI 可查法條
2. data_set (判例)         → 今晚下載，搜 PL 法判例
3. AnythingLLM (Docker)    → 今晚跑起來，上傳你的案件文件
4. CrewAI                  → 本週裝好，跑大陪審團模擬
5. lawglance               → 下週 fork，改成公用版
```
