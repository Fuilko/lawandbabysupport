# LegalShield Knowledge

データ・ベクトルDB・モデルの所在地（**git 管理外**）。

## ローカルファイル位置

| 内容 | パス | サイズ |
|---|---|---|
| 元判例 JSON | `D:\projects\LegalShield\data_set\precedent\<decade>\*.json` | 2.3 GB |
| LanceDB | `D:\projects\LegalShield\lancedb\precedents` | 3.1 GB |
| Ollama モデル | `D:\models\ollama\` | 64.2 GB |
| Embedding モデル | HuggingFace cache (`~/.cache/huggingface/`) | ~500 MB |

すべて `.gitignore` に登録済み。コミット禁止。

## データ復旧手順

別マシンで再構築する場合:

1. 判例 JSON を `H:\FLY_log\precedent\` 等から
   `D:\projects\LegalShield\data_set\precedent\` にコピー
2. Ollama インストール + モデル pull:
   ```powershell
   $env:OLLAMA_MODELS = "D:\models\ollama"
   ollama pull phi4:14b
   ollama pull gemma3:27b
   ollama pull llama3.3:70b
   ```
3. Python venv 構築 + 依存インストール:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install torch --index-url https://download.pytorch.org/whl/cu124
   pip install sentence-transformers lancedb orjson tqdm requests
   ```
4. ingest 実行（38 分）:
   ```powershell
   python legalshield\backend\full_ingest_windows.py
   ```

## Embedding モデル

`intfloat/multilingual-e5-small`
- 384 次元
- 100+ 言語対応（日本語精度高）
- Query 接頭辞: `query: ` / Document: `passage: `

## 元データ ライセンス

裁判所判例: 公開判例データ（最高裁判所判例データベース系統）。
詳細: `data_set/` 各ファイル参照。
