---
description: 跨機器部署 workflow - 在 Windows (RTX 4080) 上快速同步並啟動 LegalShield
---

# LegalShield 跨機器部署工作流

讓 Mac 開發的 code 快速同步到 Windows (RTX 4080) 並繼續運作。

## 前提條件

- Windows 已安裝: Python 3.11+, Git, Ollama, CUDA
- Windows 已有: `D:\projects\LegalShield\` 或類似路徑
- Windows 已有: LanceDB 向量庫 (`lancedb/` 資料夾)
- Windows 已有: 判例資料 (`data_set/` 資料夾, ~2.4GB)

## 快速同步 (Windows 端)

// turbo
```powershell
# 1. 進入專案目錄
cd D:\projects\LegalShield

# 2. 啟動 venv
.\.venv\Scripts\Activate.ps1

# 3. 拉取最新 code
git pull origin main

# 4. 安裝新依賴 (如果有 requirements.txt 變更)
pip install -r requirements.txt

# 5. 確認 Ollama 運行中
ollama list
# 如果沒有運行: ollama serve (另開 terminal)

# 6. 快速測試 RAG
python legalshield\backend\rag_query.py -m phi4:14b -k 6 "製造物責任法 ドローン"
```

## 完整部署 (新機器或重建)

```powershell
# 1. Clone
git clone https://github.com/Fuilko/lawandbabysupport.git D:\projects\LegalShield
cd D:\projects\LegalShield

# 2. 建立 venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. 安裝依賴
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cu124

# 4. 下載/準備資料 (如果沒有)
# - data_set/ (判例 JSON, ~2.4GB) - 從 Mac 複製或重新下載
# - lancedb/ (向量庫) - 執行 full_ingest_windows.py 生成 (~1-2小時)

# 5. 確認 Ollama 模型
ollama pull phi4:14b
ollama pull llama3.3:70b
# ollama pull gemma3:27b  # 選用

# 6. 測試
python legalshield\backend\rag_query.py --retrieve-only "テスト"
```

## 常用指令

| 任務 | 指令 |
|------|------|
| 向量檢索 (無 LLM) | `python legalshield\backend\rag_query.py --retrieve-only "關鍵字"` |
| RAG 推理 (phi4:14b) | `python legalshield\backend\rag_query.py -m phi4:14b -k 6 "問題"` |
| 多模型比較 | `python legalshield\backend\rag_compare.py "問題" -k 6 -o report.html` |
| 互動模式 | `python legalshield\backend\rag_query.py -i -m phi4:14b` |
| Streamlit UI | `python legalshield\frontend\streamlit_demo.py` |
| 全量向量化 | `python legalshield\backend\full_ingest_windows.py` |

## Mac 開發 -> Windows 執行 流程

1. **Mac**: 修改 code -> `git add .` -> `git commit` -> `git push`
2. **Windows**: `git pull` -> 測試 -> 訓練/推理
3. **Windows**: 產出新資料/分析 -> `git add` -> `git commit` -> `git push`
4. **Mac**: `git pull` -> 查看結果 -> 繼續開發

## 資料同步注意事項

- **Code**: 透過 GitHub 同步 (git push/pull)
- **大資料 (data_set/, lancedb/)**: 不透過 GitHub
  - 方法 A: 外接硬碟/USB 複製
  - 方法 B: S3/R2 等物件儲存
  - 方法 C: 每台機器各自從原始來源下載
- **模型權重**: 每台機器各自從 HuggingFace 下載 (cache)
- **.venv/**: 每台機器各自建立，不進 git
