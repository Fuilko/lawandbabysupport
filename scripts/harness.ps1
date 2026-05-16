# LegalShield Windows Harness
# 快速啟動腳本 - RTX 4080 + Ollama
# Usage: .\scripts\harness.ps1 [command]
#   init     - 完整初始化 (clone + venv + deps)
#   sync     - 同步最新 code (git pull + install deps)
#   start    - 啟動服務 (Ollama + 測試)
#   ingest   - 執行全量向量化
#   compare  - 執行多模型比較測試
#   status   - 檢查環境狀態

param(
    [Parameter()]
    [ValidateSet("init", "sync", "start", "ingest", "compare", "status", "")]
    [string]$Command = ""
)

$PROJECT_DIR = "D:\projects\LegalShield"
$VENV_PYTHON = "$PROJECT_DIR\.venv\Scripts\python.exe"
$VENV_PIP = "$PROJECT_DIR\.venv\Scripts\pip.exe"

function Test-Cuda {
    & $VENV_PYTHON -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
}

function Test-Ollama {
    try {
        $models = ollama list 2>$null
        if ($LASTEXITCODE -eq 0) { return $true }
    } catch {}
    return $false
}

function Start-OllamaService {
    if (-not (Test-Ollama)) {
        Write-Host "Starting Ollama..." -ForegroundColor Yellow
        Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 3
    }
}

switch ($Command) {
    "init" {
        Write-Host "=== LegalShield Windows Init ===" -ForegroundColor Cyan
        if (-not (Test-Path $PROJECT_DIR)) {
            git clone https://github.com/Fuilko/lawandbabysupport.git $PROJECT_DIR
        }
        Set-Location $PROJECT_DIR
        python -m venv .venv
        & $VENV_PIP install -r requirements.txt
        & $VENV_PIP install torch --index-url https://download.pytorch.org/whl/cu124
        Write-Host "Init complete. Next: place data_set/ and lancedb/ then run 'start'" -ForegroundColor Green
    }
    "sync" {
        Write-Host "=== Sync from GitHub ===" -ForegroundColor Cyan
        Set-Location $PROJECT_DIR
        git pull origin main
        & $VENV_PIP install -r requirements.txt --quiet
        Write-Host "Sync complete." -ForegroundColor Green
    }
    "start" {
        Write-Host "=== LegalShield Start ===" -ForegroundColor Cyan
        Set-Location $PROJECT_DIR
        . .\.venv\Scripts\Activate.ps1
        Start-OllamaService
        Write-Host "CUDA status:" -ForegroundColor Yellow
        Test-Cuda
        Write-Host "Ollama models:" -ForegroundColor Yellow
        ollama list
        Write-Host "Testing RAG..." -ForegroundColor Yellow
        & $VENV_PYTHON legalshield\backend\rag_query.py --retrieve-only "テスト"
        Write-Host "Ready. Use: python legalshield\backend\rag_query.py -m phi4:14b -k 6 '你的問題'" -ForegroundColor Green
    }
    "ingest" {
        Write-Host "=== Full Ingest (71,175 cases) ===" -ForegroundColor Cyan
        Set-Location $PROJECT_DIR
        . .\.venv\Scripts\Activate.ps1
        & $VENV_PYTHON legalshield\backend\full_ingest_windows.py
    }
    "compare" {
        Write-Host "=== Model Comparison ===" -ForegroundColor Cyan
        Set-Location $PROJECT_DIR
        . .\.venv\Scripts\Activate.ps1
        $question = Read-Host "Enter question"
        & $VENV_PYTHON legalshield\backend\rag_compare.py "$question" -k 6 -o compare_report.html
        Write-Host "Report: compare_report.html" -ForegroundColor Green
    }
    "status" {
        Write-Host "=== Environment Status ===" -ForegroundColor Cyan
        Set-Location $PROJECT_DIR
        Write-Host "Git branch: " -NoNewline; git branch --show-current
        Write-Host "Git status: " -NoNewline; git status --short
        Write-Host "Python: " -NoNewline; & $VENV_PYTHON --version
        Write-Host "CUDA: " -NoNewline; Test-Cuda
        Write-Host "Ollama: " -NoNewline; if (Test-Ollama) { Write-Host "Running" -ForegroundColor Green } else { Write-Host "Not running" -ForegroundColor Red }
        Write-Host "Data: " -NoNewline
        if (Test-Path "$PROJECT_DIR\data_set") { Write-Host "data_set/ OK" -NoNewline -ForegroundColor Green } else { Write-Host "data_set/ MISSING" -NoNewline -ForegroundColor Red }
        if (Test-Path "$PROJECT_DIR\lancedb") { Write-Host " | lancedb/ OK" -ForegroundColor Green } else { Write-Host " | lancedb/ MISSING" -ForegroundColor Red }
    }
    default {
        Write-Host "LegalShield Windows Harness" -ForegroundColor Cyan
        Write-Host "Usage: .\scripts\harness.ps1 [command]" -ForegroundColor Gray
        Write-Host "  init    - 完整初始化" -ForegroundColor White
        Write-Host "  sync    - 同步最新 code" -ForegroundColor White
        Write-Host "  start   - 啟動並測試" -ForegroundColor White
        Write-Host "  ingest  - 全量向量化 (1-2h)" -ForegroundColor White
        Write-Host "  compare - 多模型比較" -ForegroundColor White
        Write-Host "  status  - 檢查環境" -ForegroundColor White
    }
}
