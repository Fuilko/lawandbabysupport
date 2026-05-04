# 雙軌同步規劃：打官司 × 開發法律 AI 產品

> 更新：2026-05-05

---

## 核心策略

```
你的案件就是 LegalShield 的 Alpha Test Case。

每一步打官司的動作，都同時在：
1. 解決你自己的問題
2. 驗證產品流程
3. 產生訓練資料

打贏官司 = 最強的 Product-Market Fit 證明。
```

---

## 一、現在的武器庫 (已安裝)

### 服務

| 服務 | 端口 | 用途 |
|------|------|------|
| **AnythingLLM** | http://localhost:3001 | 法律文件 RAG 知識庫 |
| **Open WebUI** | http://localhost:3000 | Ollama 對話 + RAG |
| **Ollama** | http://localhost:11434 | 本地 LLM (llama3.2:3b) |

### Python 環境

| 工具 | 版本 | 用途 |
|------|------|------|
| **CrewAI** | 1.14.4 | 大陪審團多 Agent 模擬 |
| **e-gov-law-mcp** | 1.0.0 | 日本法令 API (MCP Server) |
| **venv** | Python 3.13 | lawandbabysupport/.venv |

### vendor/ 資料庫 (18 個 repo)

| 類別 | 專案 |
|------|------|
| **法令+判例** | data_set, listup_precedent, law.e-gov.go.jp |
| **MCP Server** | e-gov-law-mcp, tax-law-mcp, labor-law-mcp |
| **法律 AI** | lawglance, AI-Lawyer-RAG-with-Deepseek, olaw, local-legal-ai |
| **多Agent辯論** | Multi-Agents-Debate, Deb8flow, ChatEval, judges |
| **參考清單** | awesome-legaltech, awesome-legal-nlp, awesome-legal-data |
| **文件分析** | opendataloader-pdf |

---

## 二、12 週雙軌計劃

### Week 1 (5/5-5/11) — 「武裝自己 + ADR 收件」

| 時段 | 法律戰 ⚖️ | 產品開發 💻 | 共用產出 |
|------|-----------|------------|---------|
| 白天 | ADR 收件確認 + 回覆準備 | — | — |
| 晚上 1h | — | AnythingLLM 建「Mapry案件」工作空間 | 知識庫 |
| | — | 上傳: 鑑定報告、ADR申立書、法條 PDF | RAG 索引 |
| | — | 設定 Ollama → AnythingLLM 連接 | 基礎設施 |
| 週末 2h | 用 RAG 搜尋 PL 法判例 | 記錄搜尋流程 → 產品 UX 設計 | 判例資料 |

**交付物：**
- [x] AnythingLLM 上有完整案件知識庫
- [ ] 至少 10 件 PL 法判例摘要
- [ ] ADR 回覆草稿

### Week 2 (5/12-5/18) — 「訴狀起草 + CrewAI 大陪審團」

| 時段 | 法律戰 ⚖️ | 產品開發 💻 | 共用產出 |
|------|-----------|------------|---------|
| 白天 | 訴狀草稿撰寫 | — | — |
| 晚上 2h | — | CrewAI 5-Agent 模擬設定 | Agent 人格定義 |
| | — | 跑第一輪大陪審團對你的案件 | 攻防記錄 |
| 週末 3h | 根據模擬結果修正訴狀 | 記錄 Agent 的弱點/改進 | 模擬報告 |

**交付物：**
- [ ] 訴狀初稿 (民事)
- [ ] CrewAI 大陪審團第一輪報告
- [ ] Agent 人格 v1 (5 角色)

### Week 3 (5/19-5/25) — 「行政申訴 + 法令 MCP 整合」

| 時段 | 法律戰 ⚖️ | 產品開發 💻 | 共用產出 |
|------|-----------|------------|---------|
| 白天 | 國交省 無人機事故通報書 | e-Gov MCP → Windsurf 整合 | MCP 設定 |
| | 經產省 製品安全通報 | | |
| 晚上 1h | — | MCP Server 測試 (查法條原文) | API 驗證 |
| 週末 2h | 行政申訴提出 | lawglance fork → 日本法律版改造 | 程式碼 |

**交付物：**
- [ ] 國交省通報書
- [ ] 經產省通報書
- [ ] e-Gov MCP 可在 Windsurf 直接查法條
- [ ] lawglance-jp fork 初版

### Week 4 (5/26-6/1) — 「訴狀提出 + MVP 雛形」

| 時段 | 法律戰 ⚖️ | 產品開發 💻 | 共用產出 |
|------|-----------|------------|---------|
| 白天 | **訴狀正式提出** (簡易裁判所或地裁) | — | — |
| 晚上 2h | — | Intake 問卷 UI (Web) | 前端原型 |
| | — | 案件分類 AI (基於你的案件做 few-shot) | 分類模型 |
| 週末 | 等法院回覆 | MVP 整合: 問卷 → 分類 → RAG → Agent | 系統整合 |

**交付物：**
- [ ] 訴狀已提出
- [ ] LegalShield Web MVP v0.1

### Week 5-8 — 「訴訟準備書面 + 核心功能」

| 週次 | 法律戰 ⚖️ | 產品開發 💻 |
|------|-----------|------------|
| W5 | 準備第一次口頭辯論 | SHA256 存證引擎 (共用底座) |
| W6 | 開庭 (可能) | 文書生成模板引擎 |
| W7 | 準備書面 (根據開庭結果) | 多 Agent 辯論 → 策略建議 |
| W8 | 第二輪書面 | Beta 測試 (用你的案件驗證全流程) |

### Week 9-12 — 「勝訴推進 + SLM 訓練」

| 週次 | 法律戰 ⚖️ | 產品開發 💻 |
|------|-----------|------------|
| W9 | 和解交涉 or 判決準備 | SLM 微調開始 |
| W10 | — | App 原型 (SwiftUI) |
| W11 | — | App Store 提交準備 |
| W12 | (結案/上訴判斷) | **LegalShield v1.0 上線** |

---

## 三、如何將這些資源訓練成 App / SLM

### 3.1 資料流水線

```
原始資料 (你的案件+判例+法條)
    │
    ▼
┌─────────────────────────────┐
│ Phase 1: RAG (現在就能用)     │
│                             │
│ 判例 data_set  ──→ 向量化     │
│ e-Gov 法條     ──→ 向量化     │
│ 你的案件文件   ──→ 向量化     │
│        ↓                    │
│   AnythingLLM / Open WebUI  │
│   (Ollama + ChromaDB)       │
│        ↓                    │
│  「問答就能查到法條+判例」    │
└─────────────────────────────┘
    │
    ▼ (收集問答對)
┌─────────────────────────────┐
│ Phase 2: Fine-tune (W9-12)  │
│                             │
│ 問答對   ──→ JSONL 格式      │
│ 判例摘要 ──→ 指令微調資料    │
│ Agent 對話 ──→ 偏好資料       │
│        ↓                    │
│   Unsloth / MLX             │
│   基底模型: Qwen2.5-3B      │
│        ↓                    │
│  「法律專用 SLM (3B params)」│
│   輸出: GGUF (Ollama 可用)   │
│   輸出: CoreML (.mlpackage)  │
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│ Phase 3: Edge Deploy (W11+) │
│                             │
│  CoreML .mlpackage           │
│        ↓                    │
│  iPhone App (SwiftUI)       │
│  - 離線法律問答              │
│  - 存證 SHA256              │
│  - 文書生成                  │
│  - 雲端同步 (有網時)         │
└─────────────────────────────┘
```

### 3.2 訓練資料從哪來

| 資料來源 | 數量 | 格式 | 用途 |
|---------|------|------|------|
| **判例 data_set** | 71,185 件判例文字檔 | TXT → JSONL | 法律推理能力 |
| **e-Gov 法令** | 15,996 件法令 XML | XML → JSONL | 法條知識 |
| **你的案件對話** | ~數百輪 (使用過程中收集) | Chat logs → JSONL | 實戰 QA |
| **CrewAI 模擬** | ~數十次模擬 (每次 5 Agent) | Agent logs → DPO 資料 | 偏好對齊 |
| **lawqa_jp** | 多選式 QA | JSON | 法律知識評估 |

### 3.3 微調技術路線

```
Step 1: 選擇基底模型
  ├─ Qwen2.5-3B-Instruct (推薦：中日雙語好)
  ├─ Llama-3.2-3B-Instruct (備選：英日)
  └─ Phi-3.5-mini-3.8B (備選：效率高)

Step 2: 資料準備
  ├─ 判例 → 摘要+問答對 (用 GPT-4 / Claude 做 teacher)
  ├─ 法條 → 條文+解釋+適用場景
  ├─ 你的案件 → 實戰問答 (最有價值的資料)
  └─ Agent 對話 → DPO 偏好對 (好回答 vs 壞回答)

Step 3: 微調
  ├─ 工具: Unsloth (Mac MLX) 或 EC2 GPU (A10G)
  ├─ 方法: LoRA (r=16, alpha=32) → 只訓練 ~2% 參數
  ├─ 資料量: ~5,000-10,000 條 (最少 1,000 條可開始)
  └─ 時間: Mac M1 Pro ~8-12 小時 / EC2 A10G ~2-3 小時

Step 4: 量化 + 部署
  ├─ GGUF Q4_K_M → Ollama (Mac/Server)
  ├─ CoreML → iPhone App (離線)
  └─ ONNX → Web (瀏覽器端)
```

### 3.4 iPhone App 部署路線

```
CoreML 轉換流程:

1. PyTorch 微調模型 (.safetensors)
   ↓
2. coremltools 轉換
   python -m coremltools.converters.mil \
     --model qwen2.5-3b-legal-lora.safetensors \
     --output LegalSLM.mlpackage
   ↓
3. Xcode 整合
   - LegalSLM.mlpackage → Xcode Resources
   - Swift: let model = try LegalSLM(configuration: ...)
   ↓
4. App 架構
   ┌─────────────────────────────────┐
   │ SwiftUI App                     │
   │                                 │
   │ ┌─ Intake 問卷                  │
   │ ├─ CoreML SLM (離線推理)         │
   │ ├─ SHA256 存證引擎               │
   │ ├─ 文書生成 (本地模板)           │
   │ └─ 雲端同步 (有網時 → FastAPI)   │
   └─────────────────────────────────┘

模型大小:
  - 3B Q4: ~1.8GB (iPhone 可承受)
  - 1.5B Q4: ~0.9GB (更輕量)

推理速度 (iPhone 13 Pro):
  - 3B Q4: ~15-20 tokens/sec
  - 1.5B Q4: ~30-40 tokens/sec
```

---

## 四、每週產出→訓練資料對照表

| 法律戰動作 | 產生的訓練資料 | 格式 |
|-----------|-------------|------|
| ADR 回覆撰寫 | 法律文書範本 | Markdown → JSONL |
| PL 法判例搜尋 | 判例摘要+分析 | Search→Answer 對 |
| 訴狀草稿 | 訴狀模板 | Template → JSONL |
| CrewAI 模擬 | 攻防對話記錄 | DPO 偏好資料 |
| 行政申訴撰寫 | 通報書模板 | Template → JSONL |
| 開庭準備書面 | 法律論點+反駁 | QA 對 |
| 和解交涉 | 談判策略 | Strategy → JSONL |

**每做一步法律戰，就自動產生 50-200 條訓練資料。**
**12 週預計累計: 3,000-5,000 條高品質實戰資料。**

---

## 五、記憶體預算 (Mac M1 Pro 16GB)

```
同時運行:
  Ollama (llama3.2:3b)    ~3.0 GB
  AnythingLLM (Docker)    ~1.0 GB
  Open WebUI (Docker)     ~0.5 GB
  CrewAI (Python)         ~0.5 GB
  SylvaNexus SaaS         ~1.5 GB
  macOS + IDE             ~4.0 GB
  ─────────────────────────────
  合計                    ~10.5 GB / 16 GB ✅

注意:
  - 微調時需關閉 SylvaNexus 和 AnythingLLM
  - 或在 EC2 / Windows 機上做微調
```

---

## 六、風險管理

| 風險 | 影響 | 對策 |
|------|------|------|
| ADR 失敗 | 需直接訴訟 | 訴狀已同步準備，ADR 只是加速手段 |
| 對方和解 | 官司結束但訓練資料不足 | 繼續用判例資料庫訓練，不依賴單一案件 |
| SLM 精度不夠 | App 給出錯誤法律建議 | 強制引用法條原文 + 免責聲明 + RAG 保底 |
| 16GB 記憶體不夠訓練 | 無法在 Mac 上微調 | 用 EC2 A10G ($1.5/hr) 做訓練 |
| App Store 審核 | 法律類 App 可能被質疑 | 明確定位為「工具」非「法律服務」 |

---

## 七、現在就開始的 3 件事

```bash
# 1. 打開 AnythingLLM，建工作空間
open http://localhost:3001
# → 設定 Ollama (http://host.docker.internal:11434)
# → 建「Mapry 案件」工作空間
# → 上傳: ADR申立書、鑑定報告、内容証明

# 2. 搜尋 PL 法判例
cd vendor/data_set
grep -rl "製造物責任" precedent/ | head -20
# → 找到相關判例 → 上傳到 AnythingLLM

# 3. 活化 e-Gov MCP (在 Windsurf/Claude 可用)
# 設定 MCP Server 連接 (見下方設定)
```

### Windsurf MCP 設定 (加入你的 settings)

```json
{
  "mcpServers": {
    "e-gov-law": {
      "command": "/Users/fuiko/Library/Mobile Documents/com~apple~CloudDocs/SaaS 開發/lawandbabysupport/.venv/bin/python",
      "args": ["-m", "e_gov_law_mcp"],
      "cwd": "/Users/fuiko/Library/Mobile Documents/com~apple~CloudDocs/SaaS 開發/lawandbabysupport/vendor/e-gov-law-mcp"
    }
  }
}
```
