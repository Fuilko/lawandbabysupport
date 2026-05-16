#!/usr/bin/env bash
# LegalShield macOS Harness
# 快速啟動腳本 - M1 Pro/MPS
# Usage: ./scripts/harness.sh [command]
#   init     - 完整初始化
#   sync     - 同步最新 code
#   start    - 啟動並測試
#   ingest   - 全量向量化 (MPS, ~19h) -> 建議用 Windows
#   compare  - 多模型比較測試
#   status   - 檢查環境狀態

set -e

PROJECT_DIR="${HOME}/工作用/lawandbabysupport"
VENV_PYTHON="${PROJECT_DIR}/.venv/bin/python"
VENV_PIP="${PROJECT_DIR}/.venv/bin/pip"

check_cuda_or_mps() {
    ${VENV_PYTHON} -c "import torch; d = 'mps' if torch.backends.mps.is_available() else 'cpu'; print(f'Device: {d}')"
}

check_ollama() {
    curl -s http://localhost:11434/api/tags > /dev/null 2>&1
}

case "$1" in
    init)
        echo "=== LegalShield macOS Init ==="
        if [ ! -d "$PROJECT_DIR" ]; then
            mkdir -p "$(dirname "$PROJECT_DIR")"
            git clone https://github.com/Fuilko/lawandbabysupport.git "$PROJECT_DIR"
        fi
        cd "$PROJECT_DIR"
        python3 -m venv .venv
        ${VENV_PIP} install -r requirements.txt
        echo "Init complete."
        ;;
    sync)
        echo "=== Sync from GitHub ==="
        cd "$PROJECT_DIR"
        git pull origin main
        ${VENV_PIP} install -r requirements.txt --quiet
        echo "Sync complete."
        ;;
    start)
        echo "=== LegalShield Start ==="
        cd "$PROJECT_DIR"
        source .venv/bin/activate
        if ! check_ollama; then
            echo "⚠ Ollama not running. Start with: ollama serve"
            exit 1
        fi
        echo "Device: $(check_cuda_or_mps)"
        echo "Ollama models:"
        ollama list
        echo "Testing RAG..."
        ${VENV_PYTHON} legalshield/backend/rag_query.py --retrieve-only "テスト"
        echo "Ready."
        ;;
    ingest)
        echo "=== Full Ingest (WARNING: MPS takes ~19h. Use Windows/CUDA instead) ==="
        cd "$PROJECT_DIR"
        source .venv/bin/activate
        caffeinate -i ${VENV_PYTHON} scripts/full_ingest.py
        ;;
    compare)
        echo "=== Model Comparison ==="
        cd "$PROJECT_DIR"
        source .venv/bin/activate
        read -p "Enter question: " question
        ${VENV_PYTHON} legalshield/backend/rag_compare.py "$question" -k 6 -o compare_report.html
        echo "Report: compare_report.html"
        ;;
    status)
        echo "=== Environment Status ==="
        cd "$PROJECT_DIR"
        echo "Git branch: $(git branch --show-current)"
        echo "Git status: $(git status --short | wc -l) files modified"
        ${VENV_PYTHON} --version
        check_cuda_or_mps
        if check_ollama; then echo "Ollama: Running"; else echo "Ollama: Not running"; fi
        [ -d "${PROJECT_DIR}/data_set" ] && echo "data_set/: OK" || echo "data_set/: MISSING"
        [ -d "${PROJECT_DIR}/lancedb" ] && echo "lancedb/: OK" || echo "lancedb/: MISSING"
        ;;
    *)
        echo "LegalShield macOS Harness"
        echo "Usage: ./scripts/harness.sh [command]"
        echo "  init    - 完整初始化"
        echo "  sync    - 同步最新 code"
        echo "  start   - 啟動並測試"
        echo "  ingest  - 全量向量化 (MPS ~19h)"
        echo "  compare - 多模型比較"
        echo "  status  - 檢查環境"
        ;;
esac
