# 🤖 Mapry-AI — 本人訴訟支援ローカル AI

Mapry 案件（令和8年（仲）第129号）における本人訴訟のためのローカル LLM システム。

## クイックスタート（5/24 以降の作業手順）

### Step 1: 証拠資料の投入（手動）
以下のフォルダに該当ファイルを手動で配置してください（コミット禁止）：

| フォルダ | 入れるもの |
|---|---|
| `knowledge_base/raw/emails/` | Mapry とのメール・Slack 全履歴（PDF or .eml） |
| `knowledge_base/raw/contracts/` | 代理店契約書・売買契約書・見積書 |
| `knowledge_base/raw/forensics/` | M4 機器フォレンジック報告書（既に作成済） |
| `knowledge_base/raw/legal_docs/` | 仲裁申立書・相手方答弁書・内容証明 |
| `knowledge_base/raw/lawyer_consultations/` | 10名の弁護士相談メモ |

### Step 2: 構造化（自動）
```bash
python training/prepare_dataset.py
```
→ `knowledge_base/processed/mapry_evidence.duckdb` が生成されます。

### Step 3: ベースモデルのダウンロード
推奨：**ELYZA-japanese-Llama-3-8B-instruct（GGUF Q4_K_M 量化版）**
```bash
# 実装予定
python training/download_base_model.py --model elyza-llama3-8b-jp
```
→ `models/base/` に約 5GB のモデルファイル

### Step 4: LoRA 微調整
```bash
python training/lora_finetune.py
```
→ `models/fine_tuned/mapry_lora_adapter/` に約 50MB のアダプター

### Step 5: ローカル UI 起動
```bash
streamlit run app/local_ui.py
```
→ ブラウザで `http://localhost:8501` を開く（外部公開なし）

## 主な機能

- 📝 **答辯書ドラフト生成**：相手方の主張を入力 → 反論案を出力
- 📋 **準備書面起案**：争点整理 + 引用条文 + 判例
- 🔍 **証拠説明書生成**：保有証拠 → 証拠目録 + 立証趣旨
- 💬 **想定問答集**：次回期日で予想される質問への回答準備
- 📚 **関連判例検索**：類似事件の答辯戦略を提示

## 法的安全装置

1. **AI 出力は必ず弁護士確認**：最終提出前にフリーランス・トラブル110番経由の弁護士に確認
2. **証拠の改ざん禁止**：AI が生成した「事実」は使わない。事実は raw データのみから
3. **生成物の出処明記**：内部記録上、どの判例・書式を参照したかをトレース可能に
