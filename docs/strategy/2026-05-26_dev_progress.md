# LegalShield-jp 開発進捗報告（2026-05-26）

**Checkpoint 4 — 出張前最終スプリント**
**期間**: 2026-05-25 夜〜2026-05-26 朝
**ステータス**: Day 1 〜 Day 4 完了、Day 5 進行中

---

## エグゼクティブサマリー

「**6 つの問いで適切な相談先へ案内する**」という triage 機能の MVP を、**バックエンド・フロントエンド・データ層すべてで動作可能**な状態まで仕上げた。

| 領域 | 達成 |
|---|---|
| DB | 全 12 categories × 平均 6 tier の routing データ（合計 **71 routes**）|
| API | `POST /intake`、`GET /categories[/{code}[/routing]]` 計 4 endpoints |
| Frontend | 緊急バンド + タブ切替 + 6 問問診 + tier カード + tel: ワンタップ |
| データ | **配偶者暴力相談支援センター 328 件**（内閣府公式 PDF から自動抽出、全 47 都道府県）|
| 検証 | 自分の案件（Mapry M4 + ADR）で完全に妥当な推奨が出ることを確認 |
| SEO | 主要 3 トピック（DV / 製品欠陥 / 行政被害）の骨格記事を作成 |

---

## 1. Day 1 — Backend 完了

### 1-a. Routing schema 拡張（残り 7 categories）

`@gis/db/003_routing_seed_more.sql`

- 追加：**sexual_violence / child_abuse / elder_abuse / school_bullying / workplace_harassment / labor_violation / consumer_fraud**
- 各 category について Tier 1（hotline）〜 Tier 5（公共訴訟）まで複数 routes
- 追加 **45 routes**、合計 71 routes
- 制約：`UNIQUE (category_code, tier, org_kind, org_name_pattern)` に拡張（同 tier・同 org_kind に複数組織を許可：例 foreign_worker T2 admin_center に FRESC と労基署）

実行ログ：
```
DO
INSERT 0 45
```

### 1-b. POST /intake — 6 問問診 → ランキング推奨

`@gis/services/legalshield-api/app/api/intake.py`

**入力**：
```
{
  immediate_danger: bool      # Q1
  bucket: enum                # Q2
  duration: enum              # Q3
  free_text?: string          # Q4
  prior_consult?: enum        # Q5
  want?: enum                 # Q6
  language: "ja" | "en" | ...
  lat?, lng?, prefecture_code?
  consent_store_text: bool
}
```

**処理**：
1. **category detection**：keyword scan（`KEYWORDS` テーブル）→ bucket fallback
2. **trigger derivation**：`if_immediate_danger`, `if_evidence_strong`, `if_money_lost_high` etc.
3. **scoring**：`weight × trigger_match × language_bonus × want_bias`
4. **emergency mode 昇格**：Q1=yes または category.severity=critical
5. **intake_session 匿名 INSERT**（client_hash ヘッダ識別、5-tier 同意ラダー対応）

**バリデーション結果**：

| ケース | Top 1 推奨 | Top 2 |
|---|---|---|
| DV 緊急（Q1=yes） | T1 DV相談ナビ #8008 (score 1.00) | T2 警察 110（昇格後 1.08）|
| 製品欠陥（want=legal_resolution、prior=lawyer） | T3 弁護士会 PL法（score 1.173）| T4 ADR 仲裁センター（0.86）|

製品欠陥ケースは **ユーザー自身の Mapry M4 案件と完全に一致する経路**。

### 1-c. GET /categories エンドポイント

`@gis/services/legalshield-api/app/api/categories.py`

- `GET /categories` — 全 12 categories（severity / tag フィルタ可）
- `GET /categories/{code}` — 詳細
- `GET /categories/{code}/routing` — tier 別 ranked routes（tier / trigger フィルタ可）

---

## 2. Day 2 — Frontend 完了

### 2-a. 6 問 form + タブ切替

`@gis/frontend/index.html` + `@gis/frontend/intake.js`

**新構造**：
```
[緊急バンド 🚨 常時表示]
[タブ: 🛟 相談する / 🗺️ 地図で探す]
  ├─ 相談する: 6 問順次表示 (Q1〜Q6) → 結果
  └─ 地図: 既存の risk / nearest-support / report 機能
```

**特徴**：
- Q1 で「はい」を選ぶと **即 submit、緊急モードへ昇格**
- 各 Q は順番に表示（フェードイン）、進捗インジケーター 1-6
- localStorage に **anonymous client_hash** を保存（端末識別、IP 不要）

### 2-b. tier カード UI + tel: 発信

- tier 1〜5 別の色分けバッジ（赤→紫）
- 各 route カードは score（high/mid/low）でボーダー色変化
- 電話番号は `tel:` リンク化（`#8008` 等の短縮ダイヤルは `%23` エンコード）
- `<details>` で「言い方」「持ち物」「期待される対応」「次の段階」を折りたたみ表示

---

## 3. Day 3 — 緊急モード UI + intake_session

### 3-a. 緊急モード

- 画面上部に常時 🚨 ボタン（背景 #fff1f2、box-shadow で目立たせる）
- ボタン押下 → Q2-Q6 をスキップして即 POST /intake
- 結果画面の最上部に **緊急バナー**（赤枠、大型 tel: ボタン、`category.urgent_hotline` を pinned）

### 3-b. intake_session 永続化

- `/intake` の処理内で best-effort INSERT
- 失敗しても **ユーザー向け推奨は必ず返す**（graceful degradation）
- カラム：`client_hash, detected_category, detected_severity, detected_tags, language, raw_text_redacted, llm_model='rule_based_v1', llm_confidence, recommendation_json`

---

## 4. Day 4 — 実データ統合

### 4-a. 配偶者暴力相談支援センター — 328 件

`@gis/ingest/ingest_dv_centers.py`

- **出典**: 内閣府 男女共同参画局 公式 PDF（278 KB、9 ページ）
  https://www.gender.go.jp/policy/no_violence/e-vaw/soudankikan/pdf/center.pdf
- **抽出**: pdfplumber `extract_tables()` ベース、行折り返し対応
- **欠落補正**: pdfplumber が 7 県（岩手・茨城・埼玉・東京・岐阜・兵庫・鹿児島）の prefecture cell を None で返す pdf 構造的問題に対し、**name column からの prefecture 推定** fallback を実装
- **geocoding**: 都道府県重心ハードコード（478 行内蔵）— full address geocoding は MVP 範囲外
- **冪等**: source='naikakufu_dv', source_id=`pref|city|name|phone` で UPSERT

**結果**:
| 指標 | 値 |
|---|---|
| 投入レコード数 | **328** |
| カバー都道府県 | **47/47** ✅ |
| 上位 5 県 | 千葉 45、群馬 37、大阪 27、北海道 21、青森 23 |

サンプル query（東京 10 km 圏内、service=domestic_violence）：
```
東京都女性相談支援センター            03-5261-3110
港区立子ども家庭支援センター           03-5962-7215
中野区配偶者暴力相談支援センター       03-3228-5556
板橋区配偶者暴力相談支援センター       03-3579-2188
練馬区配偶者暴力相談支援センター       03-5393-3434
```

### 4-b. Hotline 番号 検証ノート

`@docs/ops/2026-05-26_hotline_verification.md`

全 16 件のホットライン（12 categories × 1〜2 件）について：
- 番号
- 機関
- 24h かどうか
- 出典 URL
- 最終確認日

を表形式で記録。発見した課題：
1. **DV** の #8008 は 24h ではない → 24h NPO 番号（0120-279-889）を T1 追加検討
2. **elder_abuse** は固定番号なし → 市区町村ベースの動的検索 UI が必要
3. **#9110** は平日昼のみ → 「24h」表示の整合性 review 必要

---

## 5. Day 5 — SEO + 公開準備

### 5-a. Help 記事 3 本

| Slug | 対象 | 内容 |
|---|---|---|
| `/help/dv` | DV 被害者 | 緊急 → 中間 → 長期の 3 段階フロー、保護命令の書面テンプレ、外国籍・経済的不安への Q&A |
| `/help/product-defect` | 製品事故被害者 | PL 法の立証責任、業界別 ADR 一覧、CALL4 公共訴訟、証拠保全の優先順位 |
| `/help/admin-grievance` | 行政被害者 | 不服審査請求テンプレ、国家賠償、録音の適法性、児相・生活保護・入管事案 |

各記事は YAML front matter で SEO metadata 完備。長期的に Hugo / Next.js などで配信予定。

### 5-b. Git commit + 進捗 PDF（本資料）

- 本ファイルが「進捗 PDF」の元 markdown
- `@scripts/md_to_pdf.py` で同ディレクトリの `2026-05-26_dev_progress.pdf` を生成

---

## 6. システム全体図（現状）

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (Leaflet + Vanilla JS, port 8092)             │
│  ├─ 🛟 相談タブ: 6 問問診 → tier カード推奨            │
│  └─ 🗺️ 地図タブ: 現在地リスク + 最寄り支援検索         │
└────────────┬────────────────────────────────────────────┘
             │ fetch
┌────────────▼────────────────────────────────────────────┐
│  FastAPI (port 8090)                                    │
│  ├─ POST /intake          (rule-based triage)           │
│  ├─ GET  /categories[…]   (curated knowledge)           │
│  ├─ GET  /nearest-support (PostGIS spatial)             │
│  ├─ GET  /risk-score      (crime density percentile)    │
│  ├─ POST /incident-report (anonymous obfuscated geom)   │
│  └─ GET  /tiles/*         (MVT vector tiles)            │
└────────────┬────────────────────────────────────────────┘
             │ asyncpg
┌────────────▼────────────────────────────────────────────┐
│  PostGIS  (legalshield schema)                          │
│  ├─ problem_category   12 rows                          │
│  ├─ category_routing   71 rows                          │
│  ├─ support_org        328 + 法テラス + … rows          │
│  ├─ intake_session     (新規・本日稼働開始)             │
│  └─ crime_grid / incident_report / prefecture / …      │
└─────────────────────────────────────────────────────────┘
```

---

## 7. 残課題（移動中も確認できる粒度で）

### 短期（次セッション）

- [ ] **モバイル UI の最終確認**（特に Q4 の textarea のソフトキーボード挙動）
- [ ] **DV 24h hotline（0120-279-889）を category_routing に追加**
- [ ] **elder_abuse の市区町村ベース地域包括 API**（市区町村テーブルとの JOIN）
- [ ] **hotline 番号の i18n**：英中韓越葡 5 言語の `accepts_languages` 列追加
- [ ] **/intake のレート制限**（IP + client_hash で 1 分 10 回まで等）
- [ ] **観測**：intake_session の `detected_category` 分布を 1 週間後に集計

### 中期（出張後）

- [ ] **NPO crawler 4 本**：女性シェルターネット、CAP、POSSE、つくろい東京
- [ ] **児童相談所所在地 CSV**（厚労省）
- [ ] **適格消費者団体 23 法人**（消費者庁）
- [ ] **国際弁護士会（外国人支援）の一覧**
- [ ] **SLM 統合**：Phi-3.5 / Gemma-3-1B で free_text からの category 検出を rule-based より精度向上
- [ ] **WAI-ARIA 完全対応 + 音声入力 fallback**
- [ ] **GitHub Pages / Cloudflare Pages デプロイ + Docker compose 本番化**

### 長期（資金獲得後）

- [ ] **on-device PSI 暗号化送信**（同意ラダー T5）
- [ ] **AWS S3 + Lambda での全国規模化**
- [ ] **CALL4 / 女性シェルターネット / 各弁護士会との API 連携協議**

---

## 8. 検証用デモシナリオ（移動中スマホで実行可）

### A. 緊急 DV
1. http://localhost:8092 を開く
2. 🚨 緊急ボタン押下
3. 結果：T1 DV相談ナビ #8008 + 警察 110 が最上位、tel: でワンタップ発信可能

### B. Mapry 案件再現
1. 🛟 相談タブ
2. Q1: いいえ / Q2: 製品・サービス / Q3: 数ヶ月以上 / Q4: 「Mapryのドローン欠陥」/ Q5: 弁護士 / Q6: 法的に解決
3. 結果：T3 弁護士会 PL 法 が score 1.173 で最上位、T4 ADR 仲裁センターが次点

### C. パワハラ
1. Q1: いいえ / Q2: 仕事 / Q3: 数週間 / Q4: 「上司から侮辱されている」/ Q5: なし / Q6: 一緒に動いてほしい
2. 結果：T1 総合労働相談コーナー → T2 雇用環境均等部 → T3 ユニオン

---

## 付記

本日のコミット：
- 56 ファイル、+12,302 行（うち md ドキュメント 4,500 行、コード 7,800 行）
- 全テスト：実稼働 API でのバリデーション 3 ケース成功

開発担当：本人（個人開発）
レビュー：未（出張中、適宜セルフレビュー）
公開予定：Day 5b 完了後にプライベートリポジトリのみ。`legalshield/private/` 配下の Mapry 案件データは引き続き完全除外。
