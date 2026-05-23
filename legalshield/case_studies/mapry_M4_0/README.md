# Mapry M4-0 Case Study

¥6,800 万 ADR 案件。製造物責任 + 詐欺 + 契約不適合の複合請求。

## ファイル

- `defects.json` — 34 安全欠陥 + 10 評価クエリ（構造化）

## defects.json スキーマ

```jsonc
{
  "case_meta": {
    "case_id": "mapry_M4_0",
    "product": "Mapry M4-0",
    "incident_date": "2026-02-03",
    "claim_amount_jpy": 68000000,
    "phase": "ADR",
    "evidence_image_sha256": "..."
  },
  "defects": [
    {
      "id": "D-01",
      "title": "バッテリー危急保護の完全無効化",
      "severity": "致命的",        // 致命的|重大|中程度
      "category": "パラメータ設定",
      "description": "...",
      "search_query": "...",        // RAG 検索に投入する自然文
      "legal_concepts": [           // ヒットを期待する法概念
        "製造物責任法3条",
        "設計上の欠陥"
      ]
    }
    // ... 34 件
  ],
  "test_queries": [
    {
      "id": "Q-01",
      "query": "ドローンの製造物責任における設計上の欠陥の判断基準",
      "relates_to": ["D-01","D-02","D-03","D-15","D-16"]   // ground truth
    }
    // ... 10 件
  ]
}
```

## 欠陥分布

- 深刻度: 致命的 6 / 重大 18 / 中程度 10
- 分類: ソフトウェア設計 9 / 品質管理 7 / パラメータ設定 5 / システム構成 4 / ハードウェア設計 3 / その他

## 用途

### 1. 個別欠陥の判例検索

```python
import json
defects = json.load(open("defects.json", encoding="utf-8"))
for d in defects["defects"]:
    print(d["id"], d["search_query"])
```

各 `search_query` を `rag_query.py --retrieve-only` に投入し、
判例リストを収集 → 訴状の根拠資料に。

### 2. RAG 召回率評価（バッチ）

`test_queries[].relates_to` がグラウンドトゥルース。
未実装。将来の評価スクリプトで:

```
for query in test_queries:
    retrieved = rag_search(query["query"], k=20)
    expected_topics = collect_legal_concepts(query["relates_to"])
    score = topic_overlap(retrieved, expected_topics)
```

## 関連証拠

- 元データ: `H:\FLY_log\` および `D:\projects\flylog_analysis\evidence\`
- 詳細欠陥説明: `D:\projects\flylog_analysis\evidence\SAFETY_DEFECT_LIST_JP.md`（D-01〜D-15）
- 全 34 欠陥 HTML: `D:\projects\flylog_analysis\evidence\甲9号証の1_安全欠陥一覧.html`
