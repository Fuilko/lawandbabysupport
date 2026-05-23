# 🔒 Private Workspace — 個人訴訟用 AI 領域

> ⚠️ **CRITICAL: このディレクトリ内のデータは GitHub 公開リポジトリに絶対に上げてはいけません。**
> `.gitignore` で `private/` 配下は全て除外されています。例外は README とコード本体のみ。

## 目的

劉 建志（リュウ ケンシ）個人が、Mapry 株式会社との品質・契約紛争（第二東京弁護士会仲裁センター 令和8年（仲）第129号）における **本人訴訟（self-litigation）** のために、ローカル AI を訓練・運用する作業領域。

## 法的根拠

| 観点 | 評価 |
|---|---|
| 本人訴訟 | 民訴法上、当事者が自身の事件を進めるのは完全に合法 |
| 弁護士法 72 条 | 「他人のため」の有償法律事務ではない → 適用外 |
| 個人情報保護法 | 個人が私的に使う場合は事業者規制の対象外 |
| 著作権法 30 条 | 私的使用のための複製は適法 |
| 生成 AI ガイドライン | 公開せず自分用 → 問題なし |

## ディレクトリ構造

```
private/
└─ mapry_ai/
    ├─ knowledge_base/
    │   ├─ raw/                  # オリジナル PDF・メール（暗号化推奨）
    │   │   ├─ emails/           # Mapry とのやり取り
    │   │   ├─ contracts/        # 契約書 PDF
    │   │   ├─ forensics/        # M4 機器フォレンジック報告書
    │   │   ├─ legal_docs/       # 仲裁申立書・相手方答弁書
    │   │   └─ lawyer_consultations/  # 10名の弁護士相談メモ
    │   └─ processed/            # 構造化済 DuckDB / LanceDB
    │
    ├─ models/
    │   ├─ base/                 # ベースモデル（Llama-3.2-3B-JP 等）
    │   └─ fine_tuned/           # LoRA アダプター（Mapry 専用）
    │
    ├─ training/
    │   ├─ prepare_dataset.py    # 事実 → Q&A ペア生成
    │   ├─ lora_finetune.py      # LoRA 微調整
    │   └─ evaluate.py
    │
    ├─ app/
    │   ├─ rag_query.py          # 公開法令 + 私的事案 融合検索
    │   ├─ brief_generator.py    # 答辯書・準備書面 起案
    │   └─ local_ui.py           # Streamlit / Gradio（localhost のみ）
    │
    └─ drafts/                   # 生成された答辯書・準備書面ドラフト
```

## セキュリティ運用ルール

1. **エアギャップ運転**：Fine-tuning と推論時は Wi-Fi OFF 推奨
2. **暗号化**：`knowledge_base/raw/` 配下は VeraCrypt コンテナ or AES-256 アプリ層暗号化
3. **バックアップ**：外付け SSD（暗号化済）のみ。クラウド禁止
4. **コミット時の確認**：`git status` で `private/` 配下のファイルが表示されないことを必ず確認

## 重要日程

| 日付 | イベント |
|---|---|
| 2026/06/03 正午 | JST RISTEX 締切 |
| 2026/06/30〜07/09 | 第二東京弁護士会仲裁センター 第 1 回期日 |

## 関連ファイル（GitHub 公開可）

- `@d:\projects\LegalShield\.gitignore`（private/ 除外設定）
- `@d:\projects\LegalShield\legalshield\`（公開技術基盤）
- `@d:\projects\LegalShield\docs\grants\`（助成金応募書類）

---

最終更新：2026年5月24日
