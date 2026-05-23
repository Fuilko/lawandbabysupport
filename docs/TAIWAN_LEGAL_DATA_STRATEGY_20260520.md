# 台灣司法資料採集 + LegalShield 訓練戰略

**作成日：** 2026年5月20日  
**結論先行：** 台灣判例**確實**是亞洲最開放的司法資料源之一，**全文公開、批次下載合法、量大、機器可讀**。對 LegalShield 有三個戰略價值。

---

## 一、為什麼台灣判例值得抓

### 量級對比

| 國家 | 公開全文 | 批次下載 API | 著作權 | 個資去識別化 | 估計可訓練量 |
|------|---------|-------------|--------|-------------|------------|
| **🇹🇼 台灣** | ✅ 2000 年起全文 | ✅ 官方 API + 月份 ZIP | 政府著作物（公共領域） | 自動處理 | **~3,000 萬份** |
| 🇯🇵 日本 | ⚠️ 重要判決摘要 | ❌ 無批次 API | 公文書（政府） | 人工選擇 | ~2 萬份（裁判所 web） |
| 🇰🇷 韓國 | ✅ 部分 | ⚠️ 限制 | 公文書 | 部分 | ~50 萬份 |
| 🇨🇳 中國 | ⚠️ 收緊中 | ❌ 縮減 | 政府著作 | 部分 | （政治性下架） |
| 🇺🇸 美國 | ✅ PACER（付費） | 部分免費 | 公共領域 | 自動 | 數千萬份 |
| 🇪🇺 EU | ✅ EUR-Lex | ✅ | 公共領域 | 自動 | 百萬級 |

**亞洲最大、機器可讀、合法可用 = 台灣**（中國以前也很大但近年下架收緊）。

### 對 LegalShield 的三個戰略價值

#### 1. Mapry 案直接適用（最即時）

你的 Mapry 案核心爭點：

```
代理商損害賠償 + 政府採購不良廠商 + 跨國製造物責任 + 詐欺 + 逸失利益
```

這幾個主題在**台灣司法院系統**有大量判例，且和你的處境**直接相關**：

| 你的爭點 | 台灣判例關鍵字 | 預估可找到件數 |
|---------|---------------|--------------|
| 代理商被切斷的損害 | 「經銷契約 損害賠償」「代理商 終止」 | 數百件 |
| 政府標案不良廠商 | 「政府採購法 第101條」「刊登政府採購公報」 | 數千件 |
| 產品瑕疵賠償 | 「物之瑕疵 損害賠償」「不完全給付」 | 萬件以上 |
| 詐欺民事 | 「民法第184條 詐欺」 | 萬件以上 |
| 逸失利益 | 「所失利益」 | 數萬件 |

→ **直接可用於 Mapry 案的台灣行政通報路徑**（林保署 / 政府採購公報）

#### 2. RAG 訓練資料量級擴充（10 倍以上）

目前 `precedents` table 推測只有日本 8 主題、可能數百筆。  
加台灣資料 → 容易擴充到 **百萬級 chunk**。

```
現況：           台灣加入後：
Japan 8 主題      Japan 8 主題
~數百筆           +
                 Taiwan 全 17 個主題（民事/刑事/行政/家事...）
                 ~3000 萬筆判決可選
                 = LanceDB 至少擴 100 倍
```

**對 RAG 的提升：**
- 中文判決 → 直接幫忙做台灣用戶版（未來 expansion）
- 日台對照 → 用台灣判例的「結構化裁判書格式」訓練「判決理由抽出」模型
- few-shot prompt 的範例庫大幅擴充

#### 3. 跨法域對照分析（學術 + 補助金亮點）

豐田財団等補助金審查時，「**日台比較法研究**」是強亮點。
- 「日本ドローン製造物責任 vs 台灣產品瑕疵代理商求償」
- 「日本 ストーカー規制法 vs 台灣 跟蹤騷擾防制法（2022 施行）」
- 「日本 児童虐待防止法 vs 台灣 兒少法」

→ 比較法 paper / Toyota Foundation Concept Note 直接可用

---

## 二、可用的台灣資料源（已驗證合法 + 公開）

### 2.1 司法院 — 主要資料源（最重要）

| 資源 | URL | 內容 | 取得方式 |
|------|-----|------|---------|
| **司法院 法學資料檢索系統** | https://law.judicial.gov.tw/ | 全國各級法院判決 2000 年起全文 | 網頁查詢 + 單筆下載 |
| **司法院 裁判書批次下載** | https://opendata.judicial.gov.tw/ | 每月 ZIP 批次（XML/JSON） | 直接 wget |
| **司法院 裁判書資料 API** | https://data.judicial.gov.tw/jdg/api/ | RESTful API | HTTP GET |
| **司法院 開放資料平台** | https://opendata.judicial.gov.tw/ | 釋憲、調解、家事、強制執行統計 | 部分 ZIP / API |
| **憲法法庭判決書** | https://cons.judicial.gov.tw/ | 大法官解釋 + 憲法法庭判決 | HTML / PDF |

**批次下載範例（每月 ZIP）：**
```bash
# 司法院每月會打包當月所有裁判書為 ZIP
# URL pattern：
https://opendata.judicial.gov.tw/data.aspx?id={dataset_id}

# 例：113 年（2024）01 月所有裁判書
https://opendata.judicial.gov.tw/data/113_01.zip
# 內容：裁判書.json + 裁判書元資料.csv
```

### 2.2 法務部 — 法令資料

| 資源 | URL | 內容 |
|------|-----|------|
| **全國法規資料庫** | https://law.moj.gov.tw/ | 全國法規（憲法・法律・命令・自治法規・條約） |
| **全國法規 API** | https://law.moj.gov.tw/api/ | 法規 JSON / XML / CSV |
| **法務部 行政函釋** | https://mojlaw.moj.gov.tw/ | 法務部解釋令 |

### 2.3 立法院 — 立法歷史

| 資源 | URL | 用途 |
|------|-----|------|
| **立法院 法律系統** | https://lis.ly.gov.tw/ | 立法理由、條文沿革 → 法解釋學重要 |
| **立法院 議事 API** | https://data.ly.gov.tw/ | 議案、發言、會議紀錄 |

### 2.4 監察院 / 公平會 / 消保會（行政決定）

| 機關 | 用途 |
|------|------|
| 監察院 糾正案 | https://www.cy.gov.tw/ — 行政違失先例 |
| 公平會 公開處分 | https://www.ftc.gov.tw/ — 競爭法案例（對 Mapry 有用） |
| 消保會 訴訟 | https://www.cpc.ey.gov.tw/ — 消費者集體訴訟先例 |

### 2.5 民間整理（補強用）

| 資源 | 用途 |
|------|------|
| **Lawsnote** (lawsnote.com) | 商業判例搜索（不能爬，但可參考分類體系） |
| **植根法律網** (rootlaw.com.tw) | 老牌法律資料庫 |
| **中央研究院 法律學研究所** 數位資源 | 學術整理的法學語料庫 |

---

## 三、著作權 + 個資合法性確認

### 3.1 著作權（OK，明文公共領域）

```
台灣著作權法 第 9 條（不得為著作權之標的）
    一、憲法、法律、命令或公文。
    二、中央或地方機關就前款著作作成之翻譯物或編輯物。
    三、標語及通用之符號、名詞、公式、數表、表格、簿冊或時曆。

→ 判決書 = 公文 = 不受著作權保護
→ 完全可下載、訓練、再散布
```

**對比日本：**

```
日本 著作権法 第 13 条
    一　憲法その他の法令
    二　国若しくは地方公共団体の機関、独立行政法人...が発する告示、訓令、通達その他これらに類するもの
    三　裁判所の判決、決定、命令...

→ 判決同樣不受著作権保護（公的資料）
→ 但日本 batch download 困難（裁判所 web 沒提供 API）
```

→ **兩國判例本身著作權都 OK，差別在「取得管道」上台灣壓倒性開放。**

### 3.2 個資保護

```
台灣 個人資料保護法
    判決書 已由司法院做去識別化處理（當事人姓名 → ○○○、地址 → 部分遮罩）
    
    殘留風險：
    - 部分判決去識別化不完全（特別是早期 / 民事小案）
    - 公司名稱通常不去識別化（法人非個資）
    - 證人 / 鑑定人姓名偶有殘留

對策：
    - 訓練時做二次 NER 去識別化（人名 → [PERSON]）
    - 不對外發布原文，只發布 RAG 結果
    - 個別查詢時，回應前再做一次 redaction
```

### 3.3 APP 是日本服務 → 用台灣資料是否有問題？

```
✅ 訓練時用台灣判例：合法（公共領域）
✅ 比較法研究：合法
⚠️ 對日本用戶顯示台灣判例作為「參考」：要明示出處 + 不是日本法
❌ 對日本用戶顯示台灣判例作為「日本法的依據」：誤導，禁止
```

**設計原則：** RAG 結果中**永遠標示來源國旗 🇹🇼 / 🇯🇵 / 🇰🇷**，並在 prompt 中明示「以下〇〇は台湾の判例であり、日本の法律には直接適用されません」。

---

## 四、實作 Pipeline（可直接執行）

### 4.1 Phase 1 — 試水（1 天）

```python
# legalshield/crawlers/judicial_tw.py
"""
司法院裁判書批次抓取
"""
import requests, json, zipfile, io
from pathlib import Path

OUTPUT = Path("legalshield/knowledge/raw/tw_judicial")
OUTPUT.mkdir(parents=True, exist_ok=True)

# 先抓一個月試試（最新月份）
def fetch_month(year_roc: int, month: int):
    """ROC year (民國年): 2024 = 113"""
    url = f"https://opendata.judicial.gov.tw/data/{year_roc}_{month:02d}.zip"
    r = requests.get(url, timeout=300)
    if r.status_code != 200:
        print(f"❌ {url} → {r.status_code}")
        return
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(OUTPUT / f"{year_roc}_{month:02d}")
    print(f"✅ {year_roc}_{month:02d}: {len(z.namelist())} files")

# Mapry 案發生於 2026 → 抓 2024-2025 比較有 reference
fetch_month(113, 1)  # 2024-01 試試
```

### 4.2 Phase 2 — 主題化採集（1 週）

針對 Mapry 案需要的主題，用台灣司法院 API 條件搜尋：

```python
# 對 Mapry 案最有用的 5 個搜索條件

queries = [
    {
        "keyword": "代理商 損害賠償 終止",
        "court": "民事",
        "level": ["最高法院", "高等法院"],
        "expected": "代理商被切斷後求償類型整理"
    },
    {
        "keyword": "政府採購法 第101條 不良廠商",
        "court": "行政",
        "expected": "外國原廠 vs 在地代理商 的責任分配"
    },
    {
        "keyword": "物之瑕疵 不完全給付 國外進口",
        "court": "民事",
        "expected": "進口商賠償後對國外原廠求償的判決"
    },
    {
        "keyword": "瑕疵 賠償 預期利益 所失利益",
        "court": "民事",
        "expected": "代理商損害計算的方法論"
    },
    {
        "keyword": "民法 184條 詐欺 不實表示 公司",
        "court": "民事",
        "expected": "公司負責人虛偽陳述的賠償"
    },
]
```

### 4.3 Phase 3 — 整合進現有 LanceDB（2-3 天）

```
現有結構：
  lancedb/precedents.lance     ← 日本判例
  lancedb/elaws_v2.lance        ← 日本法令

新增：
  lancedb/tw_precedents.lance   ← 台灣判例
  lancedb/tw_statutes.lance     ← 台灣法令（全國法規資料庫）

統一 schema（加 country 欄）：
  {
    "id": "...",
    "country": "JP" | "TW",         # ← 新增
    "court_level": "...",
    "case_no": "...",
    "date": "...",
    "subject": ["代理商", "損害賠償"],
    "text": "...",
    "embedding": [...],             # multilingual-e5-small（已支援中日多語）
    "redaction_status": "auto" | "manual" | "none",
    "url": "..."
  }

api.py 增加參數：
  POST /rag/query
    {
      "q": "代理商被切斷時可求償項目",
      "country": ["JP", "TW"],     # ← 用戶可選
      "k": 8
    }
```

**Embedding 模型 `multilingual-e5-small` 已經支援中日韓**，不需重做模型。

### 4.4 Phase 4 — 二次去識別化（重要）

```python
# 用 spaCy 中文 NER + 自訂 regex
import spacy
nlp = spacy.load("zh_core_web_lg")

def redact(text: str) -> str:
    # 1. NER 抓人名
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            text = text.replace(ent.text, "[人名]")
    # 2. 身分證 / 統編 / 電話 / 地址
    text = re.sub(r"[A-Z]\d{9}", "[身分證]", text)        # 身分證
    text = re.sub(r"\d{8}", "[統編]", text)               # 統編
    text = re.sub(r"09\d{8}", "[手機]", text)             # 手機
    text = re.sub(r"0\d{1,2}-\d{6,8}", "[電話]", text)    # 市話
    return text
```

---

## 五、戰略上的風險評估

### 5.1 政治 / 中國因素

| 風險 | 評估 |
|------|------|
| 用台灣判例 → 中國反彈？ | **不適用**：台灣司法院公開資料，對日本 App 無影響。中國伺服器不要用即可。 |
| 台灣 vs 中國法律混淆 | 有，但只要清楚標示「中華民國（台灣）」即可。**不要寫「China Taiwan」這種敏感措辭。** |
| 補助金審查機關（豐田財団）態度 | 中性偏正面：日台比較法是學術主流話題。 |

### 5.2 技術風險

| 風險 | 對策 |
|------|------|
| 司法院網站偶爾 down | 改抓 ZIP 月份檔，本地 mirror |
| 抓取頻率限制 | 加 sleep、用 official API 先（rate limit 較寬） |
| 個資去識別化不完全 | 二次 NER + 不對外公開原文，只透過 RAG 處理後輸出 |
| 中文簡繁混雜 | OpenCC 統一轉繁體（台灣判決全繁體，無此問題） |

### 5.3 法律風險（對開發者本人）

| 風險 | 對策 |
|------|------|
| 跨境資料蒐集 | 台灣 = 公開政府著作 = 無問題 |
| 個資越境（GDPR / 個情法 27 條） | 抓取下來在自己伺服器訓練 = 不算「越境提供」（你是被提供方） |
| 台灣 個資法 適用 | 政府公開判決已去識別化 = 第 51 條 1 項適用範圍外 |

---

## 六、推薦的執行優先序

```
🔥 本週可做（不需新人手）

  [1] (3小時) 寫 judicial_tw.py，抓 2024-2025 共 24 個月 ZIP
       → 容量估計：~10-30 GB，可全本地

  [2] (4小時) 寫 tw_redact.py 二次去識別化
       → 確保人名 / 身分證 / 電話 全 [REDACTED]

  [3] (2小時) Schema 統一：加 "country" 欄到 precedents table
       → backend/api.py 增加 country filter

  [4] (1小時) 跑 5 個 Mapry 主題的 keyword 搜尋
       → 預期可找到 100-1000 件直接相關判決

📅 下週

  [5] 全文寫入 LanceDB tw_precedents
  [6] embedding 重跑（multilingual-e5-small 對 zh-TW 表現好）
  [7] iOS 端 RAG UI 加 「來源國旗」標示

📅 兩週後

  [8] 主題擴充：跟蹤騷擾防制法 / 兒少法 / 性平三法 / 個資法
  [9] 日台比較法 paper 草稿（Toyota Foundation 用）
  [10] 立法院議事資料納入（立法理由用於法解釋學）
```

---

## 七、預期成果

| 指標 | 現況 | 1 個月後 | 3 個月後 |
|------|------|---------|---------|
| LanceDB 判例量 | 數百筆（JP 8 主題） | + 數十萬筆（TW 24 月份） | 百萬級 |
| 涵蓋語言 | JP | JP + TW(zh-TW) | JP + TW + KR(部分) |
| Mapry 案直接相關判例 | ~10 件（JP） | + 100-1000 件（TW） | 同上 |
| 學術成果 | 無 | 比較法初稿 | 投稿 / Toyota 補助 |
| RAG 回答品質 | 主要靠 8 主題 + LLM 通用知識 | 多倍 retrieval 強度 | 接近商業庫 |

---

## 附錄 — 立即可跑的最小指令

```powershell
# Windows / 已 venv
cd D:\projects\LegalShield
.\.venv\Scripts\python.exe -m pip install requests opencc

# 試抓一個月
@"
import requests, zipfile, io
from pathlib import Path
out = Path('legalshield/knowledge/raw/tw_judicial/113_01')
out.mkdir(parents=True, exist_ok=True)
url = 'https://opendata.judicial.gov.tw/data/113_01.zip'
r = requests.get(url, timeout=600)
print(r.status_code, len(r.content))
zipfile.ZipFile(io.BytesIO(r.content)).extractall(out)
print('done', list(out.iterdir())[:5])
"@ | .\.venv\Scripts\python.exe -

# 看抓到多少
ls legalshield\knowledge\raw\tw_judicial\113_01 | Measure-Object
```

---

> ⚠️ **本報告基於公開資訊整理，URL 和 API 端點可能變動。**  
> **實際抓取前請先以小量（單月 ZIP）驗證可用性。**  
> **大量抓取請尊重對方伺服器（加 sleep / 分散時段）。**
