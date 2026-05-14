# LegalShield 部署指南 / Deployment Guide / 部署指南

> 🌐 **Language**: [🇯🇵 日本語](#-日本語) · [🇺🇸 English](#-english) · [🇹🇼 繁體中文](#-繁體中文)
>
> **目标**：在另一台电脑（Windows / Linux / macOS）上完整重建 LegalShield 开发环境。

---

## 🇯🇵 日本語

### 前提条件

| 項目 | 最小要件 | 推奨 |
|------|---------|------|
| OS | Windows 10/11, macOS, Linux | Windows 11 + WSL2 (Ubuntu) |
| Python | 3.10+ | 3.11 |
| GPU | NVIDIA RTX 3060 12GB+ | RTX 4080 / 4090 (VRAM 16GB+) |
| RAM | 32GB | 64GB+（SLM 学習時 96GB+） |
| ストレージ | 100GB 空き | 500GB SSD |
| インターネット | 高速回線（法律データDL用） | — |

### ステップ1：コードを取得

```bash
git clone https://github.com/Fuilko/lawandbabysupport.git
cd lawandbabysupport
```

### ステップ2：Python 仮想環境

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> `requirements.txt` がない場合、手動インストール：
> ```bash
> pip install lancedb ollama sentence-transformers numpy pandas pyarrow tqdm requests beautifulsoup4
> ```

### ステップ3：Ollama + SLM モデル

```bash
# Ollama インストール（https://ollama.com からダウンロード）
# 以下はコマンドラインからモデルをダウンロード

ollama pull phi4:14b          # 高速推論（推奨）
ollama pull gemma3:27b        # 高精度
ollama pull llama3.3:70b      # 最高品質（VRAM 要）
ollama pull qwen2.5:14b       # 多言語対応
```

**確認:**
```bash
ollama list
# モデル一覧が表示されれば OK
```

### ステップ4：法律データをダウンロード（爬虫スクリプト）

```bash
# ディレクトリ作成
mkdir -p legalshield/knowledge/raw/elaws
mkdir -p legalshield/knowledge/raw/precedents
mkdir -p legalshield/knowledge/raw/statistics
mkdir -p legalshield/lancedb

# 1. 日本国法（e-Gov）— 623,000 件
python legalshield/crawlers/elaws_bulk_parallel.py

# 2. 判例データ — 724,443 件
python legalshield/crawlers/batch_fetch.py

# 3. 統計データ（市区町村・人口・DV等）
python legalshield/crawlers/batch_municipal.py
python legalshield/crawlers/batch_socio.py

# 4. 支援センター・弁護士会データ
python legalshield/crawlers/support_centers.py
python legalshield/crawlers/nichibenren_lawyers.py
```

> ⏱ 所要時間：約 2-6 時間（回線速度による）

### ステップ5：ベクトル化（埋め込み生成）

```bash
# 1. 法令テキストをチャンク化
python legalshield/backend/elaws_embed_full.py

# 2. 判例をベクトル化
python legalshield/backend/unified_vectorize.py

# 3. 全データセット統合ベクトル化
python legalshield/backend/vectorize_all_datasets.py
```

> ⏱ 所要時間：
> - RTX 4080：約 30-60 分
> - CPU のみ：約 4-8 時間

### ステップ6：データベース構築確認

```bash
# LanceDB サイズ確認
ls -lh legalshield/lancedb/
ls -lh legalshield/knowledge/*.parquet

# 想定サイズ：
# - elaws_v2.lance/    : ~1.5 GB
# - precedents.lance/  : ~0.5 GB
# - knowledge/*.parquet: ~1.8 GB（合計）
```

### ステップ7：起動テスト

```bash
# RAG 検索テスト（最速 phi4:14b）
python legalshield/backend/rag_query.py -m phi4:14b -k 6 "私が被害者です。警察に被害届を不受理された場合、どうすればいいですか？"

# インタラクティブモード
python legalshield/backend/rag_query.py -i -m phi4:14b

# 検索のみ（LLM スキップ・最速）
python legalshield/backend/rag_query.py --retrieve-only "痴漢被害の法的対処"
```

### ステップ8：バックエンド起動（FastAPI）

```bash
# API サーバー起動
python legalshield/backend/full_ingest_windows.py

# または（Linux/macOS）
python legalshield/backend/full_ingest.py
```

---

## 🇺🇸 English

### Prerequisites

| Item | Minimum | Recommended |
|------|---------|-------------|
| OS | Windows 10/11, macOS, Linux | Windows 11 + WSL2 (Ubuntu) |
| Python | 3.10+ | 3.11 |
| GPU | NVIDIA RTX 3060 12GB+ | RTX 4080 / 4090 (VRAM 16GB+) |
| RAM | 32GB | 64GB+ (96GB+ for SLM training) |
| Storage | 100GB free | 500GB SSD |
| Internet | Fast connection | — |

### Step 1: Get the Code

```bash
git clone https://github.com/Fuilko/lawandbabysupport.git
cd lawandbabysupport
```

### Step 2: Python Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> If `requirements.txt` is missing, install manually:
> ```bash
> pip install lancedb ollama sentence-transformers numpy pandas pyarrow tqdm requests beautifulsoup4
> ```

### Step 3: Ollama + SLM Models

```bash
# Install Ollama from https://ollama.com
# Download models via command line:

ollama pull phi4:14b          # Fast inference (recommended)
ollama pull gemma3:27b        # High accuracy
ollama pull llama3.3:70b      # Best quality (needs VRAM)
ollama pull qwen2.5:14b       # Multilingual
```

**Verify:**
```bash
ollama list
# Should display your models
```

### Step 4: Download Legal Data (Crawlers)

```bash
# Create directories
mkdir -p legalshield/knowledge/raw/elaws
mkdir -p legalshield/knowledge/raw/precedents
mkdir -p legalshield/knowledge/raw/statistics
mkdir -p legalshield/lancedb

# 1. Japanese National Laws (e-Gov) — 623,000 items
python legalshield/crawlers/elaws_bulk_parallel.py

# 2. Court Precedents — 724,443 items
python legalshield/crawlers/batch_fetch.py

# 3. Statistics (municipality, population, DV, etc.)
python legalshield/crawlers/batch_municipal.py
python legalshield/crawlers/batch_socio.py

# 4. Support centers / bar association data
python legalshield/crawlers/support_centers.py
python legalshield/crawlers/nichibenren_lawyers.py
```

> ⏱ Duration: ~2-6 hours (depends on internet speed)

### Step 5: Vectorization (Embedding Generation)

```bash
# 1. Chunk law texts
python legalshield/backend/elaws_embed_full.py

# 2. Vectorize precedents
python legalshield/backend/unified_vectorize.py

# 3. All datasets unified vectorization
python legalshield/backend/vectorize_all_datasets.py
```

> ⏱ Duration:
> - RTX 4080: ~30-60 min
> - CPU only: ~4-8 hours

### Step 6: Verify Database Build

```bash
# Check LanceDB size
ls -lh legalshield/lancedb/
ls -lh legalshield/knowledge/*.parquet

# Expected sizes:
# - elaws_v2.lance/    : ~1.5 GB
# - precedents.lance/  : ~0.5 GB
# - knowledge/*.parquet: ~1.8 GB (total)
```

### Step 7: Launch Test

```bash
# RAG search test (fastest phi4:14b)
python legalshield/backend/rag_query.py -m phi4:14b -k 6 "I am a victim. What should I do if police refuse to accept my report?"

# Interactive mode
python legalshield/backend/rag_query.py -i -m phi4:14b

# Search only (skip LLM, fastest)
python legalshield/backend/rag_query.py --retrieve-only "legal action for sexual harassment"
```

### Step 8: Start Backend (FastAPI)

```bash
# API server
python legalshield/backend/full_ingest_windows.py

# Or (Linux/macOS)
python legalshield/backend/full_ingest.py
```

---

## 🇹🇼 繁體中文

### 前置需求

| 項目 | 最低需求 | 建議 |
|------|---------|------|
| 作業系統 | Windows 10/11, macOS, Linux | Windows 11 + WSL2 (Ubuntu) |
| Python | 3.10+ | 3.11 |
| GPU | NVIDIA RTX 3060 12GB+ | RTX 4080 / 4090 (VRAM 16GB+) |
| 記憶體 | 32GB | 64GB+（SLM 訓練時 96GB+） |
| 儲存空間 | 100GB 空間 | 500GB SSD |
| 網路 | 高速連線（法律資料下載用） | — |

### 步驟1：取得程式碼

```bash
git clone https://github.com/Fuilko/lawandbabysupport.git
cd lawandbabysupport
```

### 步驟2：Python 虛擬環境

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> 若無 `requirements.txt`，手動安裝：
> ```bash
> pip install lancedb ollama sentence-transformers numpy pandas pyarrow tqdm requests beautifulsoup4
> ```

### 步驟3：Ollama + SLM 模型

```bash
# 安裝 Ollama（https://ollama.com 下載）
# 透過命令列下載模型：

ollama pull phi4:14b          # 高速推論（建議）
ollama pull gemma3:27b        # 高精度
ollama pull llama3.3:70b      # 最高品質（需 VRAM）
ollama pull qwen2.5:14b       # 多語言支援
```

**確認：**
```bash
ollama list
# 應顯示模型清單
```

### 步驟4：下載法律資料（爬蟲腳本）

```bash
# 建立目錄
mkdir -p legalshield/knowledge/raw/elaws
mkdir -p legalshield/knowledge/raw/precedents
mkdir -p legalshield/knowledge/raw/statistics
mkdir -p legalshield/lancedb

# 1. 日本國法（e-Gov）— 623,000 件
python legalshield/crawlers/elaws_bulk_parallel.py

# 2. 判例資料 — 724,443 件
python legalshield/crawlers/batch_fetch.py

# 3. 統計資料（市區町村・人口・DV等）
python legalshield/crawlers/batch_municipal.py
python legalshield/crawlers/batch_socio.py

# 4. 支援中心・律師會資料
python legalshield/crawlers/support_centers.py
python legalshield/crawlers/nichibenren_lawyers.py
```

> ⏱ 所需時間：約 2-6 小時（視網速而定）

### 步驟5：向量化（嵌入生成）

```bash
# 1. 法令文本區塊化
python legalshield/backend/elaws_embed_full.py

# 2. 判例向量化
python legalshield/backend/unified_vectorize.py

# 3. 全資料集統一向量化
python legalshield/backend/vectorize_all_datasets.py
```

> ⏱ 所需時間：
> - RTX 4080：約 30-60 分
> - 僅 CPU：約 4-8 小時

### 步驟6：確認資料庫建構

```bash
# 檢查 LanceDB 大小
ls -lh legalshield/lancedb/
ls -lh legalshield/knowledge/*.parquet

# 預期大小：
# - elaws_v2.lance/    : ~1.5 GB
# - precedents.lance/  : ~0.5 GB
# - knowledge/*.parquet: ~1.8 GB（總計）
```

### 步驟7：啟動測試

```bash
# RAG 檢索測試（最速 phi4:14b）
python legalshield/backend/rag_query.py -m phi4:14b -k 6 "我是被害者。警察不受理被害申告時該怎麼辦？"

# 互動模式
python legalshield/backend/rag_query.py -i -m phi4:14b

# 僅檢索（跳過 LLM・最速）
python legalshield/backend/rag_query.py --retrieve-only "痴漢被害的法律對策"
```

### 步驟8：啟動後端（FastAPI）

```bash
# API 伺服器啟動
python legalshield/backend/full_ingest_windows.py

# 或（Linux/macOS）
python legalshield/backend/full_ingest.py
```

---

## 📋 檔案結構說明 / File Structure

```
legalshield/
├── backend/                     ← 向量化腳本 + RAG 查詢
│   ├── elaws_embed.py           ← 法令嵌入（舊版）
│   ├── elaws_embed_full.py      ← 法令全文嵌入（推奨）
│   ├── elaws_embed_v2.py        ← 改良版嵌入
│   ├── unified_vectorize.py     ← 判例・統計統合向量化
│   ├── vectorize_all_datasets.py ← 全資料集批量向量化
│   └── rag_query.py             ← CLI 查詢工具
├── crawlers/                    ← 法律資料爬蟲
│   ├── elaws_bulk_parallel.py   ← e-Gov 法令批量下載
│   ├── batch_fetch.py           ← 判例・統計批量下載
│   ├── batch_municipal.py     ← 市區町村資料
│   ├── batch_socio.py         ← 社會統計資料
│   ├── support_centers.py     ← 支援中心情報
│   └── nichibenren_lawyers.py ← 日弁連律師検索
├── knowledge/
│   ├── seeds/                   ← 種子資料（CSV・小檔案・已上傳 GitHub）
│   │   ├── bar_associations.csv
│   │   ├── national_hotlines.csv
│   │   ├── ngo_seed.csv
│   │   └── support_centers_seed.csv
│   ├── raw/                     ← 爬蟲原始資料（XML・大檔案・不上傳 GitHub）
│   └── *.parquet                ← 向量嵌入資料（大檔案・不上傳 GitHub）
└── lancedb/                     ← 向量資料庫（大檔案・不上傳 GitHub）
```

### GitHub 上有什麼 / What's on GitHub

| 類別 | 上傳 | 說明 |
|------|------|------|
| Python 向量化腳本 | ✅ | `elaws_embed*.py`, `unified_vectorize.py` |
| Python 爬蟲腳本 | ✅ | `elaws_bulk*.py`, `batch_*.py` |
| CSV 種子資料 | ✅ | `seeds/*.csv`（小檔案） |
| HTML 介紹頁 | ✅ | `docs/*.html` |
| Markdown 文件 | ✅ | `README.md`, `PROJECT_TIMELINE.md` |
| 原始 XML 法令 | ❌ | `knowledge/raw/`（重新爬取） |
| Parquet 嵌入資料 | ❌ | `knowledge/*.parquet`（重新生成） |
| LanceDB 向量庫 | ❌ | `lancedb/`（重新生成） |

---

## ⚡ 快速檢查清單 / Quick Checklist

- [ ] `git clone` 完成
- [ ] Python venv 啟動
- [ ] `pip install` 完成
- [ ] `ollama list` 顯示模型
- [ ] 爬蟲腳本執行完畢（raw/ 目錄有檔案）
- [ ] 向量化腳本執行完畢（parquet 生成）
- [ ] `rag_query.py` 測試查詢成功
- [ ] 後端服務啟動成功

---

*Last updated: 2026-05-14*
