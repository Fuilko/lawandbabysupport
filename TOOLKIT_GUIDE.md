# LegalShield 工具庫完整指南

> 建立日：2026-05-05 | 版本 1.0  
> 本文件涵蓋所有已安裝的 18 個開源專案的來源、功能、用法、缺點、互補關係及上架規劃。

---

## 目錄

1. [工具總覽 — 一頁式速查表](#一工具總覽)
2. [法令資料庫 (3 個)](#二法令資料庫)
3. [判例資料庫 (2 個)](#三判例資料庫)
4. [MCP Server — AI 直接查法條 (3 個)](#四mcp-server)
5. [法律 AI 助手 (4 個)](#五法律-ai-助手)
6. [多 Agent 辯論 / 大陪審團 (4 個)](#六多-agent-辯論--大陪審團)
7. [RAG 平台 (2 個已跑)](#七rag-平台)
8. [文件分析 (1 個)](#八文件分析)
9. [Awesome Lists 參考 (3 個)](#九awesome-lists)
10. [互補關係圖](#十互補關係圖)
11. [App 上架路線](#十一app-上架路線)
12. [你的案件擴充法律分析](#十二案件擴充法律分析)
13. [需要追加的資訊](#十三需要追加的資訊)

---

## 一、工具總覽

| # | 專案名 | 類型 | 語言 | 授權 | Stars | 你的用途 |
|---|--------|------|------|------|-------|---------|
| 1 | law.e-gov.go.jp | 法令爬蟲 | Ruby | MIT | ~100 | 離線日本全法令 |
| 2 | listup_precedent | 判例爬蟲 | Rust | MIT | ~50 | 裁判所全判例爬取 |
| 3 | data_set | 判例資料集 | JSON | MIT | ~30 | 71,175 件判例 (已下載) |
| 4 | e-gov-law-mcp | MCP Server | Python | MIT | ~200 | AI 直接查法條 |
| 5 | tax-law-mcp | MCP Server | TypeScript | MIT | ~50 | 稅法 MCP (架構參考) |
| 6 | labor-law-mcp | MCP Server | TypeScript | MIT | ~30 | 勞動法 MCP (架構參考) |
| 7 | lawglance | 法律 AI 助手 | Python | Apache-2.0 | ~300 | 公用版基礎 |
| 8 | AI-Lawyer-RAG-with-Deepseek | 法律 RAG | Python | MIT | ~200 | DeepSeek + Ollama |
| 9 | olaw | 法律 RAG | Python | MIT | ~500 | 哈佛法學院出品 |
| 10 | local-legal-ai | 本地法律 AI | Python | MIT | ~100 | 完全離線 |
| 11 | Multi-Agents-Debate | 多 Agent 辯論 | Python | MIT | ~1K | MAD 框架 |
| 12 | Deb8flow | 辯論系統 | Python | MIT | ~200 | LangGraph 辯論 |
| 13 | ChatEval | 多角色評估 | Python | MIT | ~500 | LLM 角色辯論 |
| 14 | judges | LLM 陪審團 | Python | MIT | ~300 | 多模型投票 |
| 15 | awesome-legaltech | 參考清單 | Markdown | — | ~200 | LegalTech 索引 |
| 16 | awesome-legal-nlp | 參考清單 | Markdown | — | ~300 | 法律 NLP 論文 |
| 17 | awesome-legal-data | 參考清單 | Markdown | — | ~500 | 法律開放資料 |
| 18 | opendataloader-pdf | PDF 分析 | Python | Apache-2.0 | ~1K | PDF→結構化 Markdown |

**位置：** `lawandbabysupport/vendor/` 下各自獨立目錄

---

## 二、法令資料庫

### 2.1 law.e-gov.go.jp

| 項目 | 內容 |
|------|------|
| **來源** | https://github.com/riywo/law.e-gov.go.jp |
| **作者** | riywo (日本個人開發者) |
| **功能** | 從 e-Gov 法令檢索全量下載日本法令 XML，包含憲法、法律、政令、省令 |
| **語言** | Ruby |
| **授權** | MIT |
| **資料量** | ~15,996 件法令 |

**用法：**
```bash
cd vendor/law.e-gov.go.jp
# 資料已含在 repo 中，直接搜尋即可
grep -rl "製造物責任" data/
```

**缺點：**
- Ruby 寫的，跟你的 Python 棧不同語言
- 資料可能不是最新（repo 最後更新時間需確認）
- 只有法令原文 XML，沒有解釋或註釋

**互補：** 搭配 `e-gov-law-mcp` 使用 — 靜態 XML 做離線全文搜尋，MCP 做即時 API 查詢

---

### 2.2 e-Gov 法令 API v2 (官方)

| 項目 | 內容 |
|------|------|
| **來源** | https://laws.e-gov.go.jp/api/2/swagger-ui |
| **作者** | 日本政府數位廳 |
| **功能** | 官方 REST API，即時查詢最新法令全文 |
| **格式** | JSON / XML |
| **授權** | 政府公開 API (免費) |
| **限制** | 有 rate limit，無需 API key |

**用法：**
```bash
# 搜尋「製造物責任」相關法令
curl "https://laws.e-gov.go.jp/api/2/laws?keyword=%E8%A3%BD%E9%80%A0%E7%89%A9%E8%B2%AC%E4%BB%BB"
```

**缺點：**
- Rate limit 可能限制大量爬取
- XML 格式解析較複雜

**互補：** `e-gov-law-mcp` 封裝了這個 API → AI 直接用

---

## 三、判例資料庫

### 3.1 listup_precedent

| 項目 | 內容 |
|------|------|
| **來源** | https://github.com/japanese-law-analysis/listup_precedent |
| **作者** | japanese-law-analysis (日本法律分析社群) |
| **功能** | 從裁判所 HP (courts.go.jp) 爬取全部公開判例的元資料 |
| **語言** | Rust |
| **授權** | MIT |

**用法：**
```bash
cd vendor/listup_precedent
cargo run  # 需要 Rust 環境
# → 產出 JSON 格式的判例列表
```

**缺點：**
- 需要 Rust 編譯環境
- 只爬元資料（日期、案號、裁判所），不含判決全文
- 裁判所網站結構變更時可能壞掉

**互補：** 搭配 `data_set` 使用 — listup 提供最新目錄，data_set 提供已下載的全文

---

### 3.2 data_set ⭐ (最重要)

| 項目 | 內容 |
|------|------|
| **來源** | https://github.com/japanese-law-analysis/data_set |
| **作者** | japanese-law-analysis |
| **功能** | **71,175 件判例全文** (JSON)，從 1940 年代至 2020 年代 |
| **授權** | MIT |
| **大小** | ~471 MB |

**用法 (已建好工具)：**
```bash
# 用我們的搜尋工具
source .venv/bin/activate
python shared/precedent_search.py "製造物責任" --export-md --export-jsonl --output-dir shared/output
python shared/precedent_search.py "ドローン" --export-md --export-jsonl --output-dir shared/output
python shared/precedent_search.py "詐欺" --limit 50 --after 2015 --export-md --output-dir shared/output
```

**你的案件相關統計：**
| 關鍵詞 | 件數 | 說明 |
|--------|------|------|
| 製造物責任 | 65 | PL 法核心判例 |
| ドローン | 37 | 無人機相關 |
| 瑕疵担保 | 31 | 瑕疵擔保/契約不適合 |
| 契約不適合 | 2 | (新法概念，判例較少) |
| 損害賠償 | 12,937 | 廣泛 |
| 詐欺 | ~? | **需要追加搜尋** |

**缺點：**
- 資料到 ~2024 年，最新判例可能未收錄
- JSON 結構中 `contents` 有時為空（需要下載 PDF）
- 智財類判例偏多（裁判所公開偏好）

**互補：** 搭配 `opendataloader-pdf` 處理 PDF 判例 → 結構化 → RAG 向量化

---

## 四、MCP Server

### 4.1 e-gov-law-mcp ⭐ (最重要)

| 項目 | 內容 |
|------|------|
| **來源** | https://github.com/ryoooo/e-gov-law-mcp |
| **作者** | ryoooo (日本開發者) |
| **功能** | MCP Server 封裝 e-Gov API → LLM (Claude/Ollama/Windsurf) 可直接查日本法條 |
| **語言** | Python (FastMCP) |
| **授權** | MIT |
| **安裝狀態** | ✅ 已安裝在 .venv |

**用法：**
```json
// Windsurf MCP 設定
{
  "mcpServers": {
    "e-gov-law": {
      "command": ".venv/bin/python",
      "args": ["-m", "e_gov_law_mcp"],
      "cwd": "vendor/e-gov-law-mcp"
    }
  }
}
```

**功能清單：**
- `search_law(keyword)` — 用關鍵字搜尋法令
- `get_law(law_id)` — 取得法令全文
- `get_article(law_id, article)` — 取得特定條文

**缺點：**
- 依賴 e-Gov API 的網路連線
- 法令解釋需要 LLM 能力（只提供原文）
- 不含判例（只有法令）

**互補：** 搭配 `data_set` (判例) → 法條 + 判例雙重 RAG

---

### 4.2 tax-law-mcp / labor-law-mcp (架構參考)

| 項目 | 內容 |
|------|------|
| **來源** | kentaroajisaka (日本稅務專家) |
| **功能** | 稅法/勞動法專用 MCP，除 e-Gov 外還爬國稅庁/厚勞省 |
| **語言** | TypeScript (Node.js) |
| **授權** | MIT |

**用法：** 主要用作架構參考 — 如何擴充 MCP Server 加入更多資料來源

**你應該參考的功能：**
- 如何爬取行政通達 (あなたは國交省/經產省的通達が必要)
- 如何加入裁決事例 (判例以外的行政判斷)
- REST API endpoint 的設計模式

**缺點：** TypeScript 寫的，需轉換成 Python  
**互補：** Fork → 改成「PL法/航空法/消費者保護法」專用 MCP

---

## 五、法律 AI 助手

### 5.1 lawglance ⭐ (公用版基礎)

| 項目 | 內容 |
|------|------|
| **來源** | https://github.com/lawglance/lawglance |
| **作者** | LawGlance 團隊 |
| **功能** | 開源 RAG 法律助手：多語言、語音輸入、文件分析 |
| **語言** | Python (Streamlit / FastAPI) |
| **授權** | Apache-2.0 |
| **前端** | Streamlit Web UI |

**用法：**
```bash
cd vendor/lawglance
pip install -r requirements.txt
streamlit run app.py
```

**優點：**
- 完整的 Web UI (Streamlit)
- 多語言支援（含日文）
- 語音輸入
- RAG pipeline 已建好

**缺點：**
- 主要針對英美法系（需要大量改造才能適用日本法）
- Streamlit UI 不適合生產環境（效能差）
- 沒有多 Agent 功能
- 缺乏日本法令資料庫連接

**互補：** 作為 LegalShield 的 UI 原型 → 之後用 Next.js 重寫前端

**上架可行性：** ★★★☆☆ — 需要大量改造，但架構可參考

---

### 5.2 AI-Lawyer-RAG-with-Deepseek

| 項目 | 內容 |
|------|------|
| **來源** | https://github.com/AbhaySingh71/AI-Lawyer-RAG-with-Deepseek |
| **作者** | AbhaySingh71 |
| **功能** | DeepSeek R1 + Ollama 的法律 RAG chatbot |
| **語言** | Python |
| **授權** | MIT |

**用法：**
```bash
cd vendor/AI-Lawyer-RAG-with-Deepseek
pip install -r requirements.txt
# 需要設定 Ollama + DeepSeek 模型
```

**優點：**
- 專門用 DeepSeek R1 做法律推理（推理能力強）
- 支援 Ollama 本地部署
- RAG 整合完善

**缺點：**
- 依賴 DeepSeek 模型（需要下載 ~8GB）
- 英文為主，日文能力未驗證
- 單一對話模式，沒有多 Agent

**互補：** DeepSeek 的推理鏈 + `data_set` 的判例 → 強化法律推理能力

---

### 5.3 olaw (哈佛法學院)

| 項目 | 內容 |
|------|------|
| **來源** | https://github.com/harvard-lil/olaw |
| **作者** | 哈佛法學院圖書館創新實驗室 (LIL) |
| **功能** | Tool-Based RAG 法律工作台：整合 CourtListener API 等法院資料庫 |
| **語言** | Python |
| **授權** | MIT |

**用法：**
```bash
cd vendor/olaw
pip install -r requirements.txt
python app.py
```

**優點：**
- **哈佛法學院出品** — 品質有保證
- Tool-based RAG（比單純向量搜尋更精確）
- 整合美國法院 API（架構可改成日本裁判所）
- 學術論文支持

**缺點：**
- 完全美國法系（CourtListener = 美國法院）
- 需要改造成日本法院資料庫連接
- Python notebook 風格，不是生產級程式碼

**互補：** 架構設計最優 → Fork 改成日本版 → 連接 `data_set` + `e-gov-law-mcp`

---

### 5.4 local-legal-ai

| 項目 | 內容 |
|------|------|
| **來源** | https://github.com/jashankish/local-legal-ai |
| **作者** | jashankish |
| **功能** | 完全本地部署的法律 AI：無需外部 API，全部在本機跑 |
| **語言** | Python |
| **授權** | MIT |

**優點：**
- **完全離線** — 適合隱私敏感的法律案件
- 向量搜尋內建
- 支援 Ollama

**缺點：**
- 功能較簡單（基本 QA）
- 無多 Agent
- 文件不完善

**互補：** 離線能力 → 直接用於 LegalShield iPhone App 的離線模式設計參考

---

## 六、多 Agent 辯論 / 大陪審團

### 6.1 Multi-Agents-Debate (MAD) ⭐

| 項目 | 內容 |
|------|------|
| **來源** | https://github.com/Skytliang/Multi-Agents-Debate |
| **作者** | 清華大學 NLP 實驗室 |
| **功能** | **多 Agent 辯論框架**：Agent 之間自主辯論，提升推理品質 |
| **論文** | "Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate" |
| **語言** | Python |
| **授權** | MIT |

**用法：**
```python
# 核心概念：多個 LLM Agent 對同一問題辯論
# Agent A: 提出論點
# Agent B: 反駁
# Agent C: 仲裁
# → 多輪辯論後收斂到更好的答案
```

**優點：**
- **學術論文支持** — 有理論基礎
- 辯論機制提升推理品質（比單一 Agent 好 20-30%）
- 開源，可修改

**缺點：**
- 主要用於 NLP 任務評估，不是法律專用
- 需要改造成法律攻防模式
- 需要 API key（原版用 GPT-4）

**互補：** 辯論邏輯 + CrewAI 角色系統 → 大陪審團模擬

---

### 6.2 Deb8flow ⭐

| 項目 | 內容 |
|------|------|
| **來源** | https://github.com/iason-solomos/Deb8flow |
| **作者** | iason-solomos |
| **功能** | LangGraph 辯論系統：動態路由 + 事實驗證 + 仲裁機制 |
| **語言** | Python (LangGraph) |
| **授權** | MIT |

**優點：**
- **事實驗證內建** — Agent 會自動查證事實（對法律案件很重要）
- 動態路由（根據辯論進展自動調整）
- 可視化辯論流程

**缺點：**
- 依賴 LangGraph（較重的框架）
- 需要 API key

**互補：** 事實驗證功能 → 整合到大陪審團模擬中，自動查證法條引用是否正確

---

### 6.3 ChatEval

| 項目 | 內容 |
|------|------|
| **來源** | https://github.com/thunlp/ChatEval |
| **作者** | 清華大學 NLP 實驗室 |
| **功能** | 多角色辯論評估：LLM 扮演不同角色，辯論+評分 |
| **語言** | Python |
| **授權** | MIT |

**優點：**
- 成熟的角色定義系統
- 自動評分機制（可以量化辯論品質）

**缺點：** 主要用於 LLM 評估，不是法律專用  
**互補：** 角色定義 + 評分機制 → 用於大陪審團的判決品質評估

---

### 6.4 judges

| 項目 | 內容 |
|------|------|
| **來源** | https://github.com/quotient-ai/judges (原 databricks) |
| **作者** | Quotient AI |
| **功能** | **LLM 陪審團**：多個不同 LLM 投票決定 |
| **語言** | Python |
| **授權** | MIT |

**用法：**
```python
from judges import evaluate
result = evaluate(
    question="原告の勝訴可能性は？",
    answer="...",
    judges=["gpt-4", "claude-3", "llama-3"]
)
```

**優點：**
- 簡潔的 API（一行就能用）
- 多模型投票（減少單一模型偏差）

**缺點：** 主要用於評估，不是辯論  
**互補：** 大陪審團最終裁決時，用多個模型投票增加可信度

---

## 七、RAG 平台

### 7.1 AnythingLLM ⭐ (已部署)

| 項目 | 內容 |
|------|------|
| **來源** | https://github.com/Mintplex-Labs/anything-llm |
| **狀態** | ✅ Docker 運行中 http://localhost:3001 |
| **功能** | 全功能 RAG：上傳文件→向量化→聊天，支援 Ollama |
| **Stars** | 53K+ |

**你應該做的：**
1. 打開 http://localhost:3001
2. 設定 → LLM Provider → Ollama → `http://host.docker.internal:11434`
3. 建「Mapry 案件」工作空間
4. 上傳：ADR 申立書、鑑定報告、判例 Markdown
5. 直接問它法律問題

**缺點：**
- Docker 占用 ~1GB RAM
- 免費版不支援多用戶
- 嵌入模型品質一般

---

### 7.2 Open WebUI (已部署)

| 項目 | 內容 |
|------|------|
| **來源** | https://github.com/open-webui/open-webui |
| **狀態** | ✅ Docker 運行中 http://localhost:3000 |
| **功能** | Ollama Web 介面 + 內建 RAG |
| **Stars** | 100K+ |

**互補：** AnythingLLM 做深度文件分析，Open WebUI 做快速對話

---

## 八、文件分析

### 8.1 opendataloader-pdf

| 項目 | 內容 |
|------|------|
| **來源** | https://github.com/opendataloader-project/opendataloader-pdf |
| **功能** | PDF → 結構化 Markdown/JSON (支援表格、公式、圖表) |
| **語言** | Python |
| **授權** | Apache-2.0 |

**用法：**
```bash
pip install opendataloader-pdf
from opendataloader_pdf import convert
result = convert("判例.pdf")
print(result.markdown)
```

**優點：** 表格識別好，適合判例 PDF  
**缺點：** 日文 OCR 品質需測試  
**互補：** 判例 PDF → Markdown → AnythingLLM RAG

---

## 九、Awesome Lists

### 9.1-9.3 awesome-legaltech / awesome-legal-nlp / awesome-legal-data

| 清單 | 內容 | 重點項目 |
|------|------|---------|
| **awesome-legaltech** | LegalTech 全景 | EU AI Act、Kanon 2 Embedder (法律專用嵌入) |
| **awesome-legal-nlp** | 法律 NLP 論文 180+ | 最新法律 AI 研究 (2024-2025) |
| **awesome-legal-data** | 全球法律開放資料 | 各國判例/法令 API |

**用法：** 純參考，從中挑出適合的工具/論文/資料集

---

## 十、互補關係圖

```
┌─────────────────────────────────────────────────────────────┐
│                    LegalShield 架構                          │
│                                                             │
│  使用者輸入案情                                              │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────┐                                        │
│  │ 案件分類 AI      │ ← lawglance (UI/問卷參考)              │
│  └────────┬────────┘                                        │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐    ┌──────────────────┐                │
│  │ 法條檢索         │    │ 判例檢索          │                │
│  │ e-gov-law-mcp   │    │ data_set         │                │
│  │ law.e-gov.go.jp │    │ listup_precedent │                │
│  └────────┬────────┘    └────────┬─────────┘                │
│           │                      │                          │
│           ▼                      ▼                          │
│  ┌────────────────────────────────────────┐                 │
│  │ RAG 向量搜尋                            │                 │
│  │ AnythingLLM / Open WebUI               │                 │
│  │ + opendataloader-pdf (PDF→Markdown)     │                 │
│  └────────────────┬───────────────────────┘                 │
│                   │                                         │
│                   ▼                                         │
│  ┌────────────────────────────────────────┐                 │
│  │ 大陪審團模擬 (CrewAI)                   │                 │
│  │                                        │                 │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐  │                 │
│  │  │原告律師  │ │被告律師  │ │裁判官   │  │                 │
│  │  └────┬────┘ └────┬────┘ └────┬────┘  │                 │
│  │       │           │           │        │                 │
│  │       └───────────┼───────────┘        │                 │
│  │                   │                    │                 │
│  │  辯論框架:         │                    │                 │
│  │  Multi-Agents-Debate (辯論邏輯)         │                 │
│  │  Deb8flow (事實驗證)                    │                 │
│  │  ChatEval (角色定義)                    │                 │
│  │  judges (多模型投票)                    │                 │
│  └────────────────┬───────────────────────┘                 │
│                   │                                         │
│                   ▼                                         │
│  ┌────────────────────────────────────────┐                 │
│  │ 文書生成                                │                 │
│  │ → 訴狀 / 準備書面 / 行政申訴           │                 │
│  │ → local-legal-ai (離線生成參考)         │                 │
│  └────────────────────────────────────────┘                 │
│                                                             │
│  基底 LLM: Ollama (llama3.2:3b → qwen2.5:7b → 微調 SLM)    │
│  基底嵌入: nomic-embed-text / kanon-2 (法律專用)             │
└─────────────────────────────────────────────────────────────┘
```

---

## 十一、App 上架路線

### Phase 1: Web App (Week 4-8)

```
技術棧: Next.js + FastAPI + PostgreSQL + ChromaDB
部署: Vercel (前端) + EC2 (後端) + Docker
功能: 問卷 → 分類 → RAG → Agent 模擬 → 文書草案

上架: Web App 不需 App Store 審核
定價: Freemium — 基本諮詢免費，文書生成 ¥980/月
```

### Phase 2: iPhone App (Week 9-12)

```
技術棧: SwiftUI + CoreML (微調 SLM) + CloudKit
功能: 離線法律問答 + SHA256 存證 + 文書生成
模型: Qwen2.5-3B Q4 (~1.8GB) 或 1.5B Q4 (~0.9GB)

上架審核重點:
  - Apple 審查指南 5.2.5: 不可提供「法律建議」
  - 必須明確標示「資訊工具」而非「法律服務」
  - 必須有免責聲明：「本 App 不替代律師」
  - 使用者簽署所有生成文書

定價: ¥1,480/月 或 ¥12,800/年
```

### Phase 3: Android (Week 13+)

```
技術棧: Kotlin + ONNX Runtime (SLM)
或 Flutter (跨平台)
```

### 授權合規

| 專案 | 授權 | 上架限制 |
|------|------|---------|
| CrewAI | MIT | ✅ 商用可 |
| e-gov-law-mcp | MIT | ✅ 商用可 |
| lawglance | Apache-2.0 | ✅ 商用可，需保留版權聲明 |
| olaw | MIT | ✅ 商用可 |
| data_set | MIT | ✅ 商用可 |
| opendataloader-pdf | Apache-2.0 | ✅ 商用可 |
| AnythingLLM | MIT | ✅ 商用可 |
| Ollama | MIT | ✅ 商用可 |

**全部 MIT / Apache-2.0 — 商用完全沒問題。**

---

## 十二、案件擴充法律分析

你的案件不只是「產品不良」，根據你的描述，還包括以下請求權基礎：

### 12.1 請求權全覽

| # | 請求類型 | 法律根據 | 金額估算 | 證據 |
|---|---------|---------|---------|------|
| 1 | **產品代金返還** | 民法§562-564 (契約不適合) | ¥800萬 | 契約書、領收書、鑑定報告 |
| 2 | **產品缺陷損害** | PL法§3 (製造物責任) | 車輛修理+出張費 | 寫真、領收書 |
| 3 | **詐欺取消** | 民法§96 (詐欺) | ¥800萬+α | 34項缺陷明知故犯+version 0.0.0 |
| 4 | **不實告知** | 消費者契約法§4①② | ¥800萬+α | 重要事實不告知（欠陥隠蔽） |
| 5 | **不利益事實不告知** | 消費者契約法§4② | 同上 | 明知缺陷卻不告知 |
| 6 | **威脅斷貨** | 独禁法§2⑨ (優越的地位濫用) / 下請法 | 損害賠償 | メール・通話記録 |
| 7 | **逸失利益** | 民法§416② (特別損害) | **一年的時間+經費+人力+預估收入** | 事業計畫、契約、領收書 |
| 8 | **債務不履行** | 民法§415 | 損害賠償 | 納品物が契約内容と相違 |
| 9 | **不法行為** | 民法§709 | 損害賠償 | 欠陥品を故意に販売 |
| 10 | **代表者個人責任** | 会社法§429 | 同上 | 山口社長の重過失 |

### 12.2 新增：威脅斷貨 (優越的地位濫用)

```
法律根據: 独占禁止法 第2条第9項第5号
         下請法 (下請代金支払遅延等防止法)
         
要件:
  ① 取引上の優越的な地位を利用
  ② 正常な商慣習に照らして不当に不利益を与える
  
あなたのケース:
  - Mapry は「唯一の供給者」→ 優越的地位あり
  - 「断貨する」と威脅 → 不当な不利益
  - 欠陥品を改善せずに断貨威脅 → 悪質
  
通報先: 公正取引委員会 (JFTC)
  → https://www.jftc.go.jp/soudan/madoguchi/
  
⚠️ 必要な証拠:
  - 威脅斷貨のメール or 通話記録
  - 取引関係の全体像（あなたが代理店であること）
  - Mapry が唯一の供給者であること
```

### 12.3 新增：34 項缺陷刻意留存 (詐欺)

```
法律根據:
  民事: 民法§96 (詐欺による意思表示の取消し)
  刑事: 刑法§246 (詐欺罪) — 10年以下の懲役

要件 (民事):
  ① 欺罔行為: 34項の欠陥を知りながら隠して販売
  ② 錯誤: あなたは「完成品」と信じて購入
  ③ 因果関係: 真実を知っていれば購入しなかった
  
あなたのケース:
  - version "0.0.0", user "m4dev01" → 開発版と認識
  - Dec 18 の25回リブート → 出荷6日前に問題を認識
  - BATT_FS_CRT_ACT=0 (意図的な安全機能無効化)
  - 出荷後も BATT_CAPACITY 未修正 (2回目の納品でも放置)
  - bash_history に問題のデバッグ記録あり
  
⚠️ 詐欺を主張する場合の注意:
  - 立証のハードルが高い（「知っていた」の立証）
  - ただし SD カードのフォレンジック証拠が異常に強い
  - 「34項目の欠陥リスト」が全て出荷前から存在 → 認識の推定可能
```

### 12.4 新增：逸失利益（一年分）

```
法律根據: 民法§416② (特別損害の賠償)

要件:
  「特別の事情によって生じた損害であっても、
   当事者がその事情を予見すべきであったときは、
   債権者はその賠償を請求することができる」

あなたが請求できる項目:
┌─────────────────────────────────────────────┐
│ A. 直接投入コスト (立証しやすい)              │
│                                             │
│  ① 人件費（1年分）                           │
│    - あなた自身の研究時間                    │
│    - 雇用したスタッフ                        │
│    - → 勤怠記録、給与明細                    │
│                                             │
│  ② 経費（領収書ベース）                      │
│    - 台湾出張費                              │
│    - 機材購入費                              │
│    - ソフトウェア費用                        │
│    - 通信費                                  │
│    - → 全て領収書                            │
│                                             │
│  ③ 設備投資                                  │
│    - M4-0 用に準備した測量機材               │
│    - → 購入記録                              │
├─────────────────────────────────────────────┤
│ B. 逸失利益 (立証が難しいが重要)              │
│                                             │
│  ④ 失った測量契約の収入                      │
│    - 既に受注していた測量業務                │
│    - → 発注書、見積書、契約書                │
│                                             │
│  ⑤ 将来の事業収入予測                        │
│    - 事業計画書（M4-0 導入前に作成したもの） │
│    - 市場分析（台湾の林業測量市場規模）      │
│    - → 第三者の市場レポート                  │
│                                             │
│  ⑥ 信用毀損による機会損失                    │
│    - 顧客（梁氏等）との関係悪化              │
│    - → 顧客の証言                            │
├─────────────────────────────────────────────┤
│ C. 精神的損害                                │
│                                             │
│  ⑦ 慰謝料                                    │
│    - 法人間取引では低額（数十〜100万円）     │
│    - ただし詐欺的行為なら加算可能            │
└─────────────────────────────────────────────┘

⚠️ 逸失利益の立証に必要な書類:
  1. 事業計画書（M4-0 を使った事業の計画）
  2. 受注済み or 見込み契約の証拠
  3. 市場分析（林業測量の単価 × 予想件数）
  4. あなたの時間単価の根拠（大学院生の時間単価）
  5. 他の測量業者の見積書（代替コスト）
```

---

## 十三、証拠現況 + 追加情報

### ✅ 你已擁有的証拠 (盤點完成)

**証拠資料のデータ_劉-1/**

| 資料夾 | 內容 | 法律用途 |
|--------|------|---------|
| **【1_契約関係】** | 販売代理店契約書 (0818)、Order Form、正昌 Order Form、照片 | 契約成立の立証 |
| **【2_製品欠陥・墜落事故の記録】** | 事故照片 6 張 + 墜落影片 (.mp4) | 損害事実の立証 |
| **【4_交渉決裂の経緯と相手方の悪意（返金拒否・強要）】** | メール PDF + **7 通 .eml 原始郵件** (2/7-2/18) | **威脅斷貨 + 返金拒否 + 詐欺的行為** |
| **5.顧客梁氏_送金証明書** | 正昌送金通知 × 2 + 照片 | 第三者損害の立証 |
| — | mapry 辯護士來信 0312.pdf | 相手方弁護士対応記録 |
| — | M4 機器の安全性欠陥...最終要求書.pdf | 正式要求書 |
| — | 辯護師委任書.pdf | 你方律師 |

**mapry 爛事/ (頂層)**

| 檔案 | 內容 | 法律用途 |
|------|------|---------|
| **甲9号証の1 — 製品安全欠陥一覧（31項目）.pdf** | ⚠️ **31 項欠陥** (不是 18 項) | **核心技術証拠** |
| **ADR 追加証拠提出書 — 全文合併版.pdf** | ADR 追加提出 | 手続記録 |
| **甲9号証の6 — 注文書（日本語翻訳）.pdf** | 注文書翻訳 | 契約内容 |
| **請求書及び保証書 — 日本語翻訳.pdf** | Invoice + Warranty | 契約金額 + 保証範囲 |
| **領収書.pdf** | 支払証拠 | ¥800 万の支払い |
| hiifoest.com 郵件 Re_台湾 × 4 通.pdf | 往来メール | 交渉経緯 |
| 正昌 ORDER FORM.pdf | 顧客注文書 | 逸失利益根拠 |
| reconciliation_mediation.pdf × 2 | ADR/調停資料 | 手続記録 |

**mail/ (12 通メール)**

| 檔案 | 寄件人 | 法律用途 |
|------|--------|---------|
| 今後について mapry.txt/pdf | **山口→劉** (4/5) | 内容証明前日の連絡 = 認識の証拠 |
| 台湾事業の全貌と Arthur 氏の排除....txt/pdf | **劉→山口** (2/7) | 被害者がまだ加害者のために働いていた |
| 台湾市場における販売戦略の再確認....txt/pdf | **劉→山口** (11/12) | SOP 策定 + 30% 手数料 = 市場規模認識 |
| 至急台湾税関申告のための無線スペック確認.txt/pdf | **劉→山口** (12/13) | 山口が技術的に輸出を支援 |
| 台湾大手企業との連携 PM 契約....txt/pdf | **劉→山口** (12/10) | **鴻海・台塑連携 = 巨大市場認識** |
| Urgent Legal Risk Notice...txt/pdf | **劉→XING** (2/12) | 劉が Mapry の IP まで守った善意 |

**MAPRY_FINAL/**

| 子目錄/檔案 | 內容 |
|-------------|------|
| **ADR_PDF/** | 01-04 鑑定報告 PDF (15 項版) + HTML |
| **法律相關/** | 販売代理店契約書、顧問契約書、勞動契約、NDA、服務合約書、FSBIR 契約、勝率分析 (機密) |
| **產品資料/** | 見積書、發注書、簽收單、Order Form、營運計畫、光伊森林計畫、mapry_gnss.yaml 等 |
| **截圖與照片/** | (墜落現場等) |
| **20260203/** | (事故當日資料) |
| EMAIL_ADR_EVIDENCE.md | **メール × 欠陥 × 内容証明 交差立証** (已完成) |
| PRODUCT_DEFECT_FORENSIC_REPORT_JP.md | **SD カードフォレンジック報告** (18 項版) |

### 📊 欠陥項目數 對照

| 文件 | 項目數 | 說明 |
|------|--------|------|
| PRODUCT_DEFECT_FORENSIC_REPORT_JP.md | 18 項 | SD カードフォレンジック分析 |
| 甲9号証の1 — 製品安全欠陥一覧 | **31 項** | ADR 正式提出版 (最完整) |
| ADR_PDF/02_安全欠陥一覧 | 15 項 | 初版提出 |

→ **核心文件是 31 項版 (甲9号証の1)**。鑑定報告的 18 項是技術深度分析版。

### ✅ 已搜尋完成的判例 (shared/output/)

| 關鍵詞 | 件數 | 狀態 |
|--------|------|------|
| 製造物責任 | 65 | ✅ 已匯出 |
| ドローン | 37 | ✅ 已匯出 |
| 瑕疵担保 | 31 | ✅ 已匯出 |
| 契約不適合 | 2 | ✅ 已匯出 |
| 詐欺 | 50 | ✅ 已匯出 |
| 優越的地位 | 50 | ✅ 已匯出 |
| 逸失利益 | 50 | ✅ 已匯出 |
| ソフトウェア | 30 | ✅ 已匯出 |

### 🟡 仍然建議補強的部分

| # | 項目 | 你有嗎？ | 說明 |
|---|------|---------|------|
| 1 | **PL 保険の有無確認** | ❓ | ADR で相手方に確認要求 → 保険会社から回収可能 |
| 2 | **農水省 SBIR 採択リスト正式確認** | ❓ | 口頭情報あり。公式資料で裏付けすると強い |
| 3 | **Mapry 他ユーザーの事故情報** | ❓ | 系統的欠陥を示せれば PL 法の立証が更に強化 |
| 4 | **顧客（梁氏/正昌）の陳述書** | 送金証明あり ⚠️ | 陳述書（事故の影響を語るもの）があると更に強い |
| 5 | **逸失利益の金額算定書** | 事業計畫あり ⚠️ | 具体的金額を算定した書面があると裁判所は認めやすい |
| 6 | **Mapry HP/販促資料のスクショ** | ❓ | 「山岳林業用」と謳っていた証拠。HPは変更される可能性 → 今すぐ保存 |

---

## 附錄：全工具 Git Clone 一行

```bash
# 已經全部 clone 到 vendor/ 了。
# 如果需要在別台電腦重建：
cd /path/to/lawandbabysupport/vendor && \
git clone --depth 1 https://github.com/japanese-law-analysis/listup_precedent.git && \
git clone --depth 1 https://github.com/japanese-law-analysis/data_set.git && \
git clone --depth 1 https://github.com/riywo/law.e-gov.go.jp.git && \
git clone --depth 1 https://github.com/ryoooo/e-gov-law-mcp.git && \
git clone --depth 1 https://github.com/kentaroajisaka/tax-law-mcp.git && \
git clone --depth 1 https://github.com/kentaroajisaka/labor-law-mcp.git && \
git clone --depth 1 https://github.com/lawglance/lawglance.git && \
git clone --depth 1 https://github.com/AbhaySingh71/AI-Lawyer-RAG-with-Deepseek.git && \
git clone --depth 1 https://github.com/harvard-lil/olaw.git && \
git clone --depth 1 https://github.com/jashankish/local-legal-ai.git && \
git clone --depth 1 https://github.com/Skytliang/Multi-Agents-Debate.git && \
git clone --depth 1 https://github.com/iason-solomos/Deb8flow.git && \
git clone --depth 1 https://github.com/thunlp/ChatEval.git && \
git clone --depth 1 https://github.com/quotient-ai/judges.git && \
git clone --depth 1 https://github.com/Vaquill-AI/awesome-legaltech.git && \
git clone --depth 1 https://github.com/maastrichtlawtech/awesome-legal-nlp.git && \
git clone --depth 1 https://github.com/openlegaldata/awesome-legal-data.git && \
git clone --depth 1 https://github.com/opendataloader-project/opendataloader-pdf.git
```
