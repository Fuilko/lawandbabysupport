# LegalShield 統合設計レポート v0.1

**日付**: 2026 年 5 月 25 日（議論ログ）
**目的**: 1 日の議論を**論理整理用の素材**として一覧化
**読者**: 起案者 / 共同研究者 / 助言者 / 申請書執筆チーム

---

## ⚡ エグゼクティブ・サマリー

| 項目 | 結論 |
|---|---|
| 何を作るか | 困境を抱える人が「**今、誰に、何を、どう伝えるか**」を 6 問で答える、加重付き法律分流プラットフォーム |
| どう作るか | 既存 OSS（PostGIS + MapLibre + Ollama + PSI）+ ドメイン専門家のキュレート知識 |
| 誰の役か | あなた = **包丁屋（プラットフォーム供給者）**、料理人 = CALL4 / NPO / 弁護士 / 当事者 |
| 収入構造 | **政府委託 60-70%** + 研究助成 15-20% + 公益契約 10-15% + 任意寄付 5-10% |
| 規模感 | Year 1: ¥4-6M / Year 3: ¥58M / Year 5: ¥80-150M（楽観だが不可能ではない） |
| 技術核 | iPhone Neural Engine + WebLLM でオンデバイス SLM = サーバ GPU コスト ¥0 |
| 法的核 | 弁護士法 72 条境界の遵守（情報提供のみ、個別助言なし） |
| 倫理核 | 5 段同意 ladder、緊急時 bypass + 事後同意、自殺予防は「呼出までしかしない」 |
| 政治核 | 「**官民協働 + 黙ったまま証拠提供**」モデル — あなたは表に出ず、CALL4・NPO に道具を渡す |
| 3 ヶ月で | DB schema 完了 / 12 category seed / 5 routing 詳細 / 製品欠陥（自分の案件）が validate |
| 18 ヶ月で | 修論完成、MVP 公開、自治体パイロット 2 件、論文 2 本 |
| 5 年で | 2-3 自治体 + 10-50 NPO + 数万 MAU + 国際協働開始（楽観シナリオ） |

---

## 議論の流れ

```
17:43  GIS subsystem 動作確認 → 3 containers healthy / test 3 件のみ
17:46  方針転換: 法テラス爬虫より先に「問題種類 → NPO/行政対応」DB
17:49  Schema + 12 categories + 26 routing rules 投入完了
17:56  weight 解説（Bayesian prior）
18:01  入口設計: 緊急 vs 問診 vs 操作者 + 5 段同意 + 自殺・濫用境界
18:11  GIS 地図技術 + 屋内測位（東京駅モデル）
18:17  全シナリオ Lv0-Lv5 マトリクス + ギャップ分析
18:24  SEO + 集客 + コスト試算
18:32  6 軸 feasibility audit + OSS leverage + 証拠基盤
18:39  収入は「政府委託」が主軸
18:43  「官民協働 + アドボカシー」ハイブリッド
18:47  「プラットフォーム供給者」モデルに収斂
```

---

# 第 I 部 — システム現状

## 1. 稼働中のコンテナ（17:43 確認）

```
legalshield_frontend   8092  Up 7h healthy
legalshield_api        8090  Up 7h healthy  (FastAPI skeleton)
legalshield_postgres   5434  Up 7h healthy  (PostGIS 15-3.3)
```

API は 5 endpoints 稼働中：`/health`, `/nearest-support`, `/risk-score`, `/incident-report`, `/region-stats/{prefecture_code}`, `/tiles/{z}/{x}/{y}.pbf`

## 2. DB スキーマ全体像

### 既存（`001_init_schema.sql`）
- `support_org` - 法テラス + NPO + NGO + 弁護士会 統合
- `prefecture` / `city` - N03 行政界（未投入）
- `crime_grid` - 500m 格子 × 年月（未投入）
- `incident_report` - 匿名インシデント（obfuscated_geom 100-300m random offset）
- `ingest_run` - ETL ログ

### 今日追加（`002_intake_routing_schema.sql`）

```sql
problem_category    -- 12 件投入（カノニカル分類）
category_routing    -- 26 件投入（5 categories の詳細）
org_specialty       -- 0 件（特化度・有効性スコア）
case_outcome        -- 0 件（匿名化転帰、ベイズ更新の真実源）
intake_session      -- 0 件（問診セッション）
v_org_for_category  -- ランキング用 VIEW
```

### データ投入状況（18:00 時点）

| テーブル | 件数 | 備考 |
|---|---|---|
| problem_category | 12 | DV/stalking/sexual_violence/child_abuse/elder_abuse/school_bullying/workplace_harassment/labor_violation/foreign_worker/consumer_fraud/product_defect/admin_grievance |
| category_routing | 26 | DV 7 / stalking 4 / product_defect 5 / foreign_worker 5 / admin_grievance 5 |
| support_org | 3 | テストのみ |
| その他 | 0 | crawl/運用待ち |

---

# 第 II 部 — 智能法律分流モデル

## 3. 12 問題カテゴリ

| code | 重大度 | 緊急電話 | 説明 |
|---|---|---|---|
| dv | critical | #8008 | 配偶者・パートナー暴力 |
| stalking | critical | 110 | ストーカー被害 |
| sexual_violence | critical | #8891 | 性犯罪・性暴力 |
| child_abuse | critical | 189 | 児童虐待 |
| elder_abuse | high | 地域包括 | 高齢者虐待 |
| school_bullying | high | 0120-0-78310 | いじめ・スクールハラスメント |
| workplace_harassment | high | 0570-919-471 | パワハラ・セクハラ・マタハラ |
| labor_violation | high | 0120-811-610 | 賃金未払い・不当解雇 |
| foreign_worker | high | 0570-011000 | 外国人労働者の権利侵害 |
| consumer_fraud | medium | 188 | 消費者被害・契約トラブル |
| product_defect | high | 188 | 製品欠陥・PL 被害（**あなたの案件**） |
| admin_grievance | high | 0570-003-110 | 行政手続きの不利益（**妻の現場**） |

## 4. tier 推奨フロー（5 段階）

```
tier 1: 緊急ホットライン（電話一本、24h）
tier 2: 公的相談窓口（配暴セ、消費生活セ、労基署、児相）
tier 3: 専門 NPO（シェルター、支援団体）
tier 4: 法的対応（弁護士会、法テラス、ADR）
tier 5: 司法手続（家裁、簡裁、地裁、公共訴訟）
```

各ルートに：weight / trigger_condition / what_to_say_ja / documents_needed_ja / expected_outcome_ja / next_tier_if_ja を付与。

## 5. weight = ベイズ prior

```
最終 score =
    weight (curated baseline)
  × specialty_score (該機関の特化度 0-1)
  × effectiveness_score (観測ベース成功率 0-1)
  × 距離 decay (e^(-distance_km / 30))
  × 言語 match (1.0 or 0.5)
  × 費用 match (free=1.2, paid=0.8)
  × 24h 緊急加成 (1.3 if critical+24h)
  × trigger 命中加成 (+0.2 if condition met)
  × 同様ケース類似度（embedding cosine）
```

- weight = prior（人間知識）
- effectiveness_score = likelihood（観測）
- 最終 score = posterior

| weight | 意味 |
|---|---|
| 1.00 | tier 内最強 |
| 0.90-0.99 | 強く推奨 |
| 0.70-0.89 | 並列の選択肢 |
| 0.50-0.69 | 条件付き |
| <0.50 | 特殊事情のみ |

## 6. 製品欠陥（あなたの実案件）の validate

```
tier 1 → 消費生活センター 188            weight=1.00, always
tier 2 → NITE / 消費者庁                 weight=0.85, if_safety_risk     ← Mapry 命中
tier 3 → 弁護士会 PL 法                  weight=0.85, if_money_lost_high ← Mapry 命中
tier 4 → 弁護士会 仲裁センター（ADR）   weight=0.75, always              ← 進行中
tier 5 → CALL4 公共訴訟                  weight=0.65, if_collective       ← 6/1 週面談予定
```

**あなたの実体験が routing knowledge の正しさを実証**。

---

# 第 III 部 — 入口設計と倫理

## 7. 3 つの入口モード

| モード | 対象 | UI | 進行 |
|---|---|---|---|
| 🔴 緊急 | 命の危険切迫 | 大ボタン 1 個「今すぐ電話」 | 5 秒 |
| 🟡 ガイド | 混乱・困惑 | 対話型問診 6-7 問 | 3-5 分 |
| 🟢 セルフ | 操作者本人 | category 直選 + 構造化 | 30 秒 |

## 8. ガイドモード 6 問

1. すぐに身の安全が脅かされていますか？ → はい → 緊急に昇格
2. 困りごとを最も近いカテゴリで（人間関係 / 仕事 / 製品 / 行政 / その他）
3. いつ頃から（今日 / 数日 / 数週間 / 数ヶ月以上）
4. 自由記述（任意、書かなくても OK）
5. これまで相談したことは？（警察 / 弁護士 / NPO / 家族 / なし）
6. 今、何が一番欲しい？（情報 / 話を聞いて / 一緒に動いて / 法的解決）

## 9. 5 段同意 Ladder

| Tier | 何をする | 何を取る | デフォルト |
|---|---|---|---|
| 0 | 情報閲覧 | 何も | 自動 |
| 1 | オンデバイス問診 | 端末内のみ | アプリ起動で同意 |
| 2 | 位置情報「市レベル」共有 | 都道府県・市町村 | 明示同意 |
| 3 | 推薦先 NPO/行政との連携 | redacted text + city + category | 明示（連携先ごと） |
| 4 | 匿名化ベクトル研究貢献 | embedding（原文不保存） | 別画面 opt-in |
| 5 | 転帰追跡 | 結果 + feedback | 別画面 opt-in |

### 緊急時の同意 bypass
- 個人情報保護法 18 条 1 項 2 号「人の生命、身体又は財産の保護」
- 監査ログ全件記録、事後同意必須

## 10. 研究データ寄与（Tier 4）の合規

```
ユーザー入力 → 端末側 PII redaction（人名・住所・電話・SNS ID マスク）
            → sentence-transformers 384 次元 embedding
            → 原文は端末から削除（vector のみアップロード）
            → S3 (encrypted, KMS) → 高知大学 IRB 承認 corpus
            → 30 日以内なら撤回可、超過後は anonymized data（GDPR 4(1) 不適合）
```

## 11. 顔・声・ID

| 種別 | 既定 | 動作 |
|---|---|---|
| 写真の顔 | 端末側自動ぼかし | Vision Framework |
| 音声 | 端末側文字起こし → 音声破棄 | Whisper local |
| 身分証 | 読まない | 必要なら端末暗号化のみ |
| 加害者の顔 | 保存可、共有制限 | Evidence Vault SHA-256 |

## 12. 命の危険・自殺の境界線

```
Lv1 受動的支援（自動）: 警告 UI + ホットライン表示
Lv2 接続提案（同意）: 「位置を最寄りの精神保健福祉センターに繋げる？」
Lv3 強制介入の境界:
  ❌ プラットフォームから警察自動通報なし
  ❌ 救急車手配は本人 or 第三者の手動
  ✅ 例外: 児童虐待 + 命の危険 → 児虐法 6 条通報努力義務
     ただし「努力義務」、最終判断は人間
```

**核心 doctrine**：プラットフォームは「呼び出し」までしかしない、最終決定は人間。

## 13. 濫用防止：コスト非対称性

- ❌ マイナンバー要求 → 真の被害者排除
- ❌ 厳格審査 → 心が折れる
- ✅ 6 問の入力時間 → spam bot は嫌う、本物は丁寧に書く
- ✅ 同一加害者重複 → 追加質問で連名告訴 vs ヘイト識別
- ✅ crime_grid 統計 triangulate
- ✅ NPO パートナーの人間レビュー（flag のみ、99% 自動 / 1% 人間）
- ✅ ML 異常検出は「拒否」でなく「flag」

**原則：拒否しない、観察する**。

## 14. 境界線図（最重要）

```
事象              │Platform│ NPO │ 行政 │ 警察 │ 医療 │
═══════════════════════════════════════════════════════
情報提供          │ ★★★  │     │      │      │      │
カテゴリ分類      │ ★★★  │     │      │      │      │
証拠保全（端末）  │ ★★★  │     │      │      │      │
寄り添い         │       │ ★★★ │     │      │      │
シェルター入居    │       │ ★★★ │ ★   │      │      │
保護命令申立      │       │ ★   │ ★★★ │     │      │
児童一時保護      │       │     │ ★★★ │     │      │
緊急逮捕         │       │     │      │ ★★★ │     │
保護命令発令      │       │     │      │      │ ★★★ (家裁) │
精神保健入院      │       │     │ ★    │      │ ★★★ │
身体的緊急医療    │       │     │      │      │ ★★★ │
公共訴訟・社会化  │       │ ★★★ │     │      │      │
研究蓄積         │ ★★★  │ ★   │      │      │      │
```

### 4 つの doctrine
1. プラットフォームは権限を持たない
2. 「呼び出し」と「情報提供」のみ
3. 最終決定は常に人間
4. 連携先の多様性が重要（一刀切回避）

---

# 第 IV 部 — 全シナリオマトリクス

## 15. 緊急度 6 段階

```
Lv0  命の危険切迫       秒〜分     殺人未遂・自殺・拉致
Lv1  重大被害・避難     時間       DV 直後・性犯罪 72h
Lv2  24h 以内対応       24h       通報後手続き・口座凍結
Lv3  落ち着いて相談     数日〜週   ハラスメント・LGBTQ
Lv4  民事紛争・長期     月〜年     離婚・PL 訴訟・労働審判
Lv5  政策・社会変革     年単位     公共訴訟・連名告訴
```

## 16. Lv0（命の危険切迫）

| シナリオ | 入口 | tier 1 | 平台 |
|---|---|---|---|
| 殺人未遂進行中 | 🔴 | 110 | 🟠 |
| DV 殺意攻撃中 | 🔴 | 110 + 「DV」 | 🟠 |
| 性的暴行進行中 | 🔴 | 110 + 「性犯罪」 | 🟠 |
| 監禁・拉致中 | 🔴 サイレント | 110 サイレント発信 | ❌ |
| 自殺企図実行中 | 🔴 | 119 + よりそい | 🟠 |
| 無理心中の予兆 | 🟡/🟢 | 189 + 110 | 🟠 |
| 重大医療緊急 | 🔴 | 119 | 🟠 |

**Lv0 共通**：ロック画面緊急ボタン、自動 GPS、3 秒長押しサイレント、自動録音（端末内）。

## 17. Lv1（重大被害・避難要）

| シナリオ | tier 1 | 平台 |
|---|---|---|
| DV 暴力後の避難 | 配暴セ + シェルター | ✅ |
| ストーカー追跡中 | 警察生活安全課 + 配暴セ | ✅ |
| 性犯罪直後 72h | #8891 + 警察 + 産婦人科 | 🟠 |
| 児童虐待一時保護 | 189 児相 + 警察 | 🟠 |
| 技能実習生逃亡 | FRESC + 移住連 + 労基署 | ✅ |
| 過労死リスク | 労基署 + 119 | 🟡 |
| リベンジポルノ拡散 | 警察 + 削除 + セーフライン | 🟠 |
| 暴力団脅迫 | 暴力追放センター + 警察 | ❌ |

## 18. Lv2-3（24h ~ 数週間）

| シナリオ | 平台 |
|---|---|
| 通報後シェルター入居 | ✅ |
| 児童虐待通報（教師） | 🟠 |
| 詐欺被害（口座凍結） | 🟡 |
| 不正アクセス検知 | ❌ |
| いじめ（自殺リスク） | 🟡 |
| 高齢者虐待発見 | 🟡 |
| ハラスメント職場 | 🟡 |
| LGBTQ 差別 | ❌ |
| 名誉毀損 SNS | ❌ |
| 自殺念慮（予防） | 🟠 |

## 19. Lv4（民事紛争）

| シナリオ | 平台 |
|---|---|
| 離婚調停・訴訟 | ✅ DV |
| **製品欠陥 PL（あなたの案件）** | ✅ ★ |
| 不動産トラブル | ❌ |
| 雇用訴訟 | 🟡 |
| 医療過誤 | ❌ |
| 交通事故民事 | ❌ |
| 相続紛争 | ❌ |
| 知的財産侵害 | ❌ |
| 中小 vs 大企業 | ❌ |
| **フリーランス（仲裁案件）** | ✅ |

## 20. Lv4 行政

| シナリオ | 平台 |
|---|---|
| **児相過剰介入で家族分離（妻の現場）** | ✅ ★ |
| 生活保護打切り | 🟡 |
| 在留資格不許可 | 🟡 |
| 公務員ハラスメント | 🟡 |
| 警察の不適切対応 | 🟠 |
| 学校体罰 | 🟡 |

## 21. Lv5（政策・社会変革）

| シナリオ | 平台 |
|---|---|
| 連名告訴（PSI）| 🟠 設計済 |
| 公共訴訟提起（CALL4 連携）| ✅ |
| 政策提言 | 🟠 |
| メディア社会化 | 🟠 |
| 学術研究（修論）| ✅ |

## 22. 平台対応力マトリクス

```
                    Lv0  Lv1  Lv2  Lv3  Lv4  Lv5
─────────────────────────────────────────────
入口モード         🟠   🟠   🟡   ✅   ✅   🟡
カテゴリ分類       ✅   ✅   ✅   ✅   ✅   ✅
routing 知識       🟠   ✅   🟡   🟡   ✅   ✅
緊急ボタン         🟠   🟠   ❌   ❌   ❌   ❌
LLM intake         ❌   ❌   ❌   ❌   ❌   ❌
GIS 表示           ✅   ✅   ✅   ✅   ✅   ✅
証拠保全 (Vault)   🟠   🟠   🟠   🟠   ✅   ✅
多言語             ❌   ❌   ❌   ❌   ❌   ❌
転帰追跡           ❌   ❌   ❌   ❌   ❌   ❌
連名 (PSI)         —    —    —    —    🟠   🟠
研究 corpus        ❌   ❌   ❌   ❌   ❌   ❌
─────────────────────────────────────────────
カバー率推定       20%  35%  40%  55%  65%  50%
```

## 23. ギャップ分析

### P0（命の責任）
1. 緊急モード UI（🔴 ボタン、サイレント、位置自動共有 + 事後同意）
2. 残り 7 categories の routing 詳細（特に sexual_violence、child_abuse）
3. 24h 対応窓口の正確データ

### P1（カバレッジ拡張）
4. LLM intake（Ollama + Llama 3.1 8B）
5. 配偶者暴力相談支援センター 全国 280 件 crawler
6. 児童相談所 230 件 + 消費生活センター 800 件 crawler

### P2（差別化機能）
7. BLE Beacon パートナー NPO（到着確認 + 本人確認バイパス）
8. PSI 連名告訴（同加害者の暗号マッチング）
9. Evidence Vault iOS 統合
10. 多言語 5 言語（en/zh/ko/vi/pt）

### P3（研究・スケール）
11. case_outcome 追跡 UI
12. 研究 corpus opt-in + IRB 連携
13. CALL4 連携 API
14. 障壁レポート自動生成

---

# 第 V 部 — 技術選定

## 24. GIS スタック

```
iOS Native (MapKit) ← 緊急モード
Web (MapLibre GL JS) ← 通常
   ↓
pg_tileserv / martin → /tiles/{z}/{x}/{y}.pbf
   ↓
PostGIS

ベース：国土地理院（GSI）標準・淡色・衛星（無料・公式）
       https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png
```

| 選択肢 | 評価 |
|---|---|
| MapLibre GL JS | OSS、GPU 加速、ベクトル、3D。Mapbox の OSS フォーク。**推奨** |
| Leaflet | 軽量。Phase 1 でこのまま OK |
| deck.gl | heatmap、3D 柱。研究デモ用 |
| MapKit iOS | iOS 緊急、Apple Indoor Maps 連携 |
| 国土地理院 vector | 無料・商用可・公式 |

### プライバシー obfuscate（既存 schema）

```
incident_report:
  geom            (real, server-only, never returned)
  obfuscated_geom (polygon, 100-300m random offset)  ← API はこっちのみ
```

## 25. 屋内測位 6 技術

| 技術 | 精度 | コスト | iOS | LegalShield 適性 |
|---|---|---|---|---|
| GPS + A-GPS | 屋外 5-10m | ¥0 | ✅ | Phase 1 |
| Wi-Fi 測位 | 屋内 5-15m | ¥0 | ✅ 自動 | Phase 2 |
| BLE Beacon | 1-3m | ¥500-2K/個 | ✅ | **Phase 2 NPO 玄関** ★ |
| PDR | drift 3-5% | ¥0 | ✅ | Phase 3 |
| ARKit VIO | <1m 短距離 | ¥0 | ✅ | Phase 4 |
| UWB | 10cm | ¥3K+/anchor | ✅ iPhone 11+ | Phase 5 |

### 東京駅 navi の構成
```
JR-AUTO Wi-Fi 数百 AP → BSSID + RSSI fingerprint（主測位）
BLE Beacon 数百個 → UUID + RSSI（補強）
PDR → 歩行ステップ × 推定歩幅 × heading（隙間補間）
気圧計 → 12 Pa/階で階判定
IMDF → 屋内ベクター地図
→ Sensor Fusion: Kalman / Particle Filter
```

東京駅は Apple Indoor Maps 正式登録済 = JR 東日本が IMDF 提供。

### LegalShield 現実的実装
```
Phase 1 (今):     屋外 GPS + 住所入力フォールバック  → 95% カバー
Phase 2 (3 月):   Wi-Fi 自動推定                    → +3%
Phase 3 (6 月):   BLE Beacon @ パートナー NPO       → +1% でも価値最大 ★
Phase 4 (12 月):  気圧計 + ARKit 階・経路誘導
Phase 5 (24 月):  UWB + 5G                         → 様子見
```

**現実認識**：利用シーンの 95% は自宅・病院・職場・路上。屋内測位完璧不要。差別化は Phase 3 BLE × 信頼到着確認。

---

# 第 VI 部 — ビジネス・テクニカル戦略

## 26. ペルソナ 6 階層

```
Lv1 被害者本人 (B2C)         無料・匿名・モバイル主
Lv2 二次被害者 (B2C)         無料
Lv3 支援者 (B2B, NPO)        無料 + 寄付/有料機能
Lv4 専門職 (B2B)             ¥1,000-3,000/月 任意寄付
Lv5 行政 (B2G)              公益契約・カスタム
Lv6 研究・教育 (B2A)         無料 academic
```

楽観的人数予測（Year 5）：合計 73,000、月間 active 13,000、寄付 ¥1.95M/月。
→ 後の feasibility audit で再校正：Year 5 で 1-3 万 MAU が現実的。

## 27. SEO 12 本コア記事

| URL | キーワード | 推定月間検索 |
|---|---|---|
| /help/dv | DV 相談 無料 | 18,000 |
| /help/stalker | ストーカー 通報 | 12,000 |
| /help/sexual-violence | 性犯罪 相談 | 8,000 |
| /help/child-abuse | 児童虐待 通報 | 22,000 |
| /help/workplace-harassment | パワハラ 相談 | 33,000 |
| /help/labor-violation | 残業代 未払い | 40,000 |
| /help/consumer-fraud | 詐欺 被害 相談 | 27,000 |
| /help/product-defect | 製品 欠陥 賠償 | 5,000 |
| /help/foreign-worker | 外国人 労働 相談（5 言語） | 8,000 |
| /help/admin-grievance | 行政 不服 審査 | 4,000 |
| /help/bullying | いじめ 相談 子供 | 14,000 |
| /help/elder-abuse | 高齢者 虐待 通報 | 6,000 |

合計推定月間流入 197,000 → 10% CTR → 月間 20,000 訪問。

## 28. 5 段アクセス階層

```
Tier 0  即使用 (PWA, no signup)         legalshield.jp 直アクセス
Tier 1  個人アカウント (magic link)      案件継続 / Evidence Vault
Tier 2  寄付者 (¥500-3K/月 任意)         稼働継続 / 詳細レポート
Tier 3  NPO 法人パートナー (無料)        マルチユーザー / CRM / GDrive
Tier 4  行政・自治体 (公益契約)          専用テナント / 監査ログ / LGWAN-ASP
Tier 5  研究・OSS セルフホスト (無料)    docker compose + AI Agent デプロイ
```

## 29. コスト分析（10 万 MAU）

```
A. LLM なし
   EC2 + RDS + S3 + CDN + ALB → $130/月 ≈ ¥20K/月 = ¥240K/年

B. + Bedrock LLM
   + 10K intake/月 × $0.00075 = $7.5/月 → 誤差レベル

C. + オンデバイス SLM (iPhone Neural Engine)
   追加コスト = $0 ★（最強戦略）

D. EC2 GPU SLM
   $530/月 → 高すぎる、避ける
```

スケール曲線：
```
1 万人:     ¥10K/月    (¥120K/年)
10 万人:    ¥20K/月    (¥240K/年)
100 万人:   ¥100K/月   (¥1.2M/年)
1000 万人:  ¥1M/月     (本気の SRE 必要)
```

## 30. 統合機能

| 機能 | 内容 |
|---|---|
| スキャナ・FAX 直結 | 複合機 → email → AWS Textract → Llama 自動分類 |
| Google Drive / OneDrive | OAuth → 新規ファイル検知 → PII redaction → 案件統合 |
| GitHub セルフデプロイ | docker compose + Windsurf/Claude agent で 1-click |
| kintone / Salesforce | 既存 CRM 双方向同期（NPO 半数が kintone） |
| LINE Bot | 入口 1 つ、ハードル最低 |
| マイナンバーカード | **使わない**（本人確認バイパスが核心） |

## 31. データセット公開

```
https://huggingface.co/datasets/legalshield-jp/
├── support_orgs_2026.parquet
├── routing_knowledge_v0.1.json  (curated 26 → 拡張)
├── anonymized_intake_corpus/    (research opt-in 集約)
└── barrier_reports_v0.1/        (制度障壁の質的データ)

License: CC-BY 4.0
Citation: 「LegalShield-jp Open Dataset v0.1, Liu et al. 2026」
```

---

# 第 VII 部 — 6 軸可行性監査

## 32. 技術 ★★★★☆ 高

90% は既存 OSS のグルーコード。新規研究要素 = PSI 連名 + 多言語法律 NLP の 2 点のみ。

## 33. 経費 ★★★☆☆ 中

18 ヶ月最小予算 ≈ ¥1.7M（人件費は修士のため計上せず）。
助成金採択率 15-20% → **不採択確率 70-85%、Plan B 必須**。

## 34. 政治 ★★☆☆☆ 中下

最大リスク：**弁護士法 72 条**（非弁行為）
- 一般情報 = OK
- 個別助言 = NG
- AI が「あなたはこうすべき」 = グレー

→ 必須：「これは法律情報、特定事案の法的助言ではない」明示。
→ 谷口律師との初回面談の核心議題。

## 35. 経済 ★★☆☆☆ 中下

```
弁護士ドットコム 2024:    ¥7.3B（上場、相談+顧問）
CALL4 (NPO):             ¥30-50M/年
法テラス:                 ¥39.7B/年（国家予算）
```

寄付モデル単独では：
- ¥3-10M/年で 0.5 FTE
- ¥30-50M/年で 3-5 FTE
- ¥100M/年で本格運営（5-10 年かかる）

**しかし政府委託を加えれば構造が変わる（後述）**。

## 36. 法律 ★★★☆☆ 中

| 法律 | リスク | 対応 |
|---|---|---|
| 弁護士法 72 条 | 非弁 | 一般情報のみ明示 |
| 個人情報保護法 | 大量データ | DPO 任命、PIA、Privacy by Design |
| 通信の秘密 | メッセージング | 機能を実装しない |
| 児虐法 6 条 | 通報義務 | 人間判断 doctrine |
| DV 法 6 条 2 項 | 通報努力義務 | 同上 |
| 不正アクセス禁止法 | 証拠保全 | 自分の端末・データのみ |
| AI 規制（2026 春予定） | ハイリスク AI | 透明性レポート公開 |
| GDPR | EU 利用者 | DPA 公開、Right to Erasure |

## 37. 人性 ★★☆☆☆ 中下（最難関）

| 障壁 | 詳細 |
|---|---|
| 「人に頼ること=恥」文化 | 「自分で何とか」「家族に迷惑」 |
| 「**唐突**な対人接触の忌避」 | 突然 NPO に救援要請 = 失礼 |
| デジタル不信 | 高齢・地方の抵抗 |
| DV「離れられない」心理 | 経済依存・子・世間体 |
| 二次被害コスト | SNS 炎上・職場差別 |
| 「自治体に頼る=負け」 | スティグマ |
| 多文化共生の浅さ | 外国人支援薄い |
| 専門用語の壁 | 親権・保全処分・ADR 不明 |

### 「唐突 NPO 接続」の問題（あなたの指摘）

❌ 従来モデル：助けてボタン → NPO 通知 → NPO が連絡 → 引く
✅ 改良モデル：情報閲覧 → 準備（スクリプト・書類リスト・地図）→ **被害者が能動的に電話**

→ 「**準備支援**」モデル：プラットフォームは訓練・予習を提供、接触は被害者主導。

---

# 第 VIII 部 — 開発研究 Roadmap（18 ヶ月）

```
Month 1-2 学術基盤
  - 文献レビュー（後述 evidence base）
  - IRB 申請（高知大学）
  - 鈴木教授指導開始
  - 修論テーマ確定
  - ガバナンス・倫理 framework v0.1 commit

Month 3-4 技術 MVP
  - 12 categories 全 routing 知識 seed
  - 4 つの主要 crawler（配暴セ・消費生活セ・児相・労基署）
  - Web 問診 6 問 (PWA)
  - rule-based 推奨エンジン（LLM なし）
  - Leaflet GIS 公開

Month 5-6 法律パイロット
  - 谷口律師面談（6 月第 1 週）
  - ADR 仲裁第 1 回期日（あなたの案件）
  - 弁護士法 72 条境界の確定
  - プラポリ / 利用規約完成
  - 法律監修体制 1 名確保

Month 7-9 ユーザーテスト
  - 保健師パイロット（妻の病院）n=3
  - DV シェルター 1 箇所 n=10 ケース
  - 第二東京弁護士会 仲裁セで利用 n=1（あなた）

Month 10-12 拡張
  - オンデバイス SLM 実装（Llama 3.2 1B/3B）
  - 多言語 5 言語
  - iOS app TestFlight 配布
  - 修論中間発表

Month 13-15 学会発表
  - 日本法社会学会
  - 日本社会情報学会
  - IEEE Security & Privacy 投稿（PSI）
  - FAccT 2027 投稿（AI ethics）

Month 16-18 修論完成・展開
  - 修論審査
  - Hugging Face データセット公開
  - NPO 法人化検討（オプション）
```

---

# 第 IX 部 — 証拠と OSS

## 38. 日本国内統計根拠

| 出典 | データ |
|---|---|
| 内閣府男女共同参画局 | 男女間における暴力に関する調査（3 年） |
| 警察庁 | ストーカー事案・配偶者暴力対応状況 |
| 国民生活センター | PIO-NET 統計 |
| 厚労省 | 外国人技能実習生労災 |
| 法務省 | 犯罪白書、犯罪被害者白書 |
| 日弁連 | 司法アクセス白書、弁護士白書 |
| こども家庭庁 | 児童相談所対応件数 |

## 39. 国際 benchmark

| 出典 | 内容 |
|---|---|
| World Justice Project | Rule of Law Index 2024（日本 14 位） |
| OECD | Equal Access to Justice for Inclusive Growth (2019) |
| UN SDG 16 | Access to Justice for All |
| LSC (US) | Justice Gap Report 2022（92% 低所得層届かず） |
| Hadfield | Rules for a Flat World (2017) |
| Susskind | Online Courts and the Future of Justice (2019) |

## 40. AI Triage 研究

| 論文 |
|---|
| Bauer & Wright (2023) "AI-augmented crisis text platforms" Nature Digital Medicine |
| Pisani et al. (2022) "ML for suicide risk" Lancet Psychiatry |
| Walsh et al. (2017) "Predicting Risk of Suicide Attempts" |
| Pestian et al. (2019) "Suicide Note Classification" |

## 41. プライバシー暗号

| 論文 |
|---|
| Pinkas, Schneider, Zohner (2014) "Faster Private Set Intersection" |
| Apple (2021) "CSAM Detection Technical Summary" |
| Kissner & Song (2005) "Privacy-Preserving Set Operations" |
| Ion et al. (2020) "On Deploying Secure Computing" Google |
| Signal Foundation | Anonymous Credentials, Sealed Sender |

## 42. 法と AI

| 論文 |
|---|
| Bommasani et al. (2021) "Foundation Models" Stanford |
| Engstrom et al. (2020) "Government by Algorithm" |
| Chesterman (2021) "We the Robots?" Cambridge UP |
| EU AI Act (2024) |
| 中央大法学部「リーガルテックの実装と法的課題」 |

## 43. OSS leverage マップ

### GIS / Mapping
- MapLibre GL JS (BSD-3) / Leaflet (BSD-2) / pg_tileserv (Apache-2.0) / Martin (MIT)
- PostGIS (GPL-2) / Uber H3 (Apache-2.0)
- 国土地理院タイル / OpenStreetMap (ODbL)

### NLP / LLM
- Ollama / llama.cpp / MLX (Apple) / WebLLM (TVM)
- sentence-transformers / LangChain / LlamaIndex
- spaCy + GiNZA / MeCab / Sudachi
- NLLB-200 (Meta, 200 言語) / Whisper / LexNLP

### プライバシー暗号
- OpenMined PySyft / Microsoft SEAL / TFHE-rs (Zama) / Concrete (Zama)
- libsodium / Signal Protocol / Tink (Google) / age

### 証拠保全
- OpenTimestamps / Sigstore / Cosign
- ExifTool / Autopsy / Internet Archive Wayback
- age + git-annex

### OCR
- Tesseract / PaddleOCR / EasyOCR
- Apache Tika / pypdf / pdfplumber
- Apple Vision Framework

### App framework
- Next.js / SvelteKit / Capacitor / Tauri
- FastAPI（現使用）/ PWA + Workbox

### 参考 GitHub プロジェクト
- openmined/PySyft - プライバシー保存 ML
- signalapp/libsignal - E2E プロトコル
- freedomofpress/securedrop - 内部告発者保護
- ushahidi/platform - 危機マッピング、Kenya 25 万 user
- MapStore/MapStore2 - 多レイヤー GIS
- codeforjapan/welcome-tokyo - 自治体協働事例

---

# 第 X 部 — 収入戦略（政府委託主軸）

## 44. 収入ポートフォリオ修正版

```
🏛️ 公的事業委託 (政府発注)      60-70%  ★主軸
🎓 研究助成金 (RISTEX, トヨタ)   15-20%
🤝 公益契約 (自治体ライセンス)    10-15%
💝 寄付 (任意、Lv4 専門職)        5-10%
```

## 45. 中央省庁・国機関の発注

| 発注元 | 事業 | 規模 | 適合 |
|---|---|---|---|
| 内閣府男女共同参画局 | DV 被害者支援多言語化 | ¥10-30M | ★★★★★ |
| 内閣府 | デジタル田園都市交付金（自治体経由） | ¥10-50M/件 | ★★★★ |
| **こども家庭庁** | **SNS 相談事業委託** | ¥50-200M/年 | ★★★★★（最大） |
| こども家庭庁 | 児童虐待 ICT 化モデル | ¥20-50M | ★★★★ |
| 厚労省 | 自殺対策強化事業 | ¥38B/年 全体 | ★★★★ |
| 厚労省 | いじめ・自殺対策 SNS | ¥10-50M/件 | ★★★★ |
| **法務省** | **司法ソーシャルワーク モデル** | ¥10-20M | ★★★★★ |
| 法務省 | 人権相談多言語化 | ¥5-15M | ★★★★ |
| 消費者庁 | 消費生活相談 AI 化 | ¥10-20M | ★★★ |
| 出入国在留管理庁 | 外国人共生センター ICT | ¥10-30M | ★★★★ |
| デジタル庁 | デジタル臨時行政調査 | 不定 | ★★★ |
| 法テラス | 多言語相談業務委託 | ¥10-50M | ★★★★ |
| JICA | 海外司法アクセス支援 | ¥30-100M | ★★★（中長期） |

## 46. 都道府県・自治体

| 自治体 | 事業 | 規模 |
|---|---|---|
| 東京都 | DV / 多言語 / 性犯罪ワンストップ | ¥10-50M、複数 |
| 大阪府 | DV / 外国人共生 | ¥10-30M |
| 愛知県 | 多文化共生 | ¥10-30M |
| 京都府 | 学生 SOS / LGBTQ | ¥5-20M |
| **高知県（地元）** | 中山間地域司法 / 自殺対策 | ¥5-20M ★ |
| 千葉県（妻の現場） | DV / 子供 SOS | ¥5-20M |
| 政令市 20 市 | 各市 DV 計画 | ¥3-15M/件 |
| 特別区 23 区 | 個別事業 | ¥3-10M/件 |

→ 47 都道府県 + 20 政令市 + 23 区 + 中核市 ≈ 150 自治体が毎年類似事業を発注。

## 47. 5 年現実収入シナリオ（修正版）

| Year | 修正前（助成金のみ） | 修正後（委託 + 助成金） |
|---|---|---|
| 1 | ¥1.5M | **¥4.5-6.5M** |
| 2 | ¥3M | **¥21-28M** |
| 3 | ¥3-5M | **¥58M** |
| 5 | ¥10M | **¥80-150M** |

→ 「5 年で事業成立」 → 「**Year 2 末で 2-3 FTE 雇用可能**」に修正。
→ 修論執筆中の Year 1 も大学経由委託 + RISTEX で食える。

## 48. 委託 entry の障壁と回避策

| 障壁 | 回避策 |
|---|---|
| 入札参加資格 | A 等級不要、B-D 等級で即取得可 |
| 実績要件 | **共同提案**で大手の実績を借りる |
| 連帯保証 | 信用金庫・全国保証協会経由 |
| 大手 SIer 競合 | OSS + AI + 多言語で技術差別化 |
| コネ | 鈴木教授・谷口律師・台湾人脈経由 |
| 資金繰り | 概算払い制度、つなぎ融資 |

### 回避策の具体パターン
1. **大学経由**：高知大学受託（PI: 鈴木）→ 受託研究員として参画
2. **共同提案**：TIS / NEC / 中堅 SIer と共同応札、技術担当
3. **NPO 連合**：DV シェルター連盟 + JANIC + LegalShield 共同
4. **指定管理者制度**：自治体の DV センター 5 年契約

## 49. 直近 12 ヶ月の入札スケジュール（実務）

| 時期 | 案件 | 推定額 | 戦略 |
|---|---|---|---|
| 2026-04 | こども家庭庁 SNS 相談 | ¥50M+ | 大手と共同提案 |
| 2026-05 | 高知県 DV 計画関連 | ¥5-15M | 大学経由 |
| 2026-06 | デジタル田園都市交付金 自治体 | ¥10-50M | 千葉県松戸市等 |
| 2026-09 | 内閣府 多言語相談 | ¥10-30M | NPO 連合経由 |
| 2026-10 | 法務省 司法ソーシャル | ¥10-20M | 谷口律師経由 |
| 2026-11 | 厚労省 自殺対策強化交付金 | ¥10-30M/自治体 | 高知県経由 |
| 2027-01 | 出入国在留管理庁 FRESC | ¥10-30M | 多言語強み |
| 2027-03 | RISTEX SOLVE 2027 | ¥1.5M+ | 助成金、保険 |

→ 8 件中 1-2 件採択でも年商 ¥10-30M。

## 50. 海外参考事例

| 国 | プロジェクト | 形態 | 規模 |
|---|---|---|---|
| 🇹🇼 | PDIS（公共數位創新空間） | 政府内 + 委託 | 年 ¥数億 |
| 🇹🇼 | g0v 零時政府 | NPO + 政府協働 | 年 ¥数千万 |
| 🇪🇪 | e-Estonia X-Road | 政府 + 民間連合 | 年 €数億 |
| 🇬🇧 | GovTech Catalyst | スタートアップ向け発注 | £20M/プログラム |
| 🇺🇸 | 18F / USDS | 政府内 + 委託 | 年 $40-60M |
| 🇮🇱 | Yad Sarah | NPO 公的契約 | 年 ¥約 30 億 |

→ 「両方やる」が世界標準、日本だけ「受託 OR 批判」二択文化が強い。

---

# 第 XI 部 — 立ち位置

## 51. プラットフォーム供給者モデル（最終形）

```
┌──────────────────────────────────────────────────┐
│  LegalShield = 中立的インフラ供給者                │
│  (一般社団 or 株式会社、政府委託も受ける)          │
│                                                    │
│  あなたの顔: 技術者・研究者・基盤提供者            │
│  「私たちは道具を作る、使い方は使う人が決める」    │
└──────────────────────────────────────────────────┘
              │
              │ "Powered by LegalShield"
              ▼
┌──────────────────────────────────────────────────┐
│  プラットフォームを使う独立アクターたち            │
├──────────────────────────────────────────────────┤
│  CALL4         → 公共訴訟（LegalShield データ使用） │
│  DV NPO        → シェルター運営（SaaS 利用）        │
│  弁護士        → 案件準備（証拠基盤利用）           │
│  ジャーナリスト → 調査報道（匿名データ参照）        │
│  研究者        → 学術論文（コーパス利用）           │
│  被害当事者    → 自助（直接利用）                   │
│  議員秘書      → 政策資料（オープンデータ参照）     │
│  自治体監察官  → 統計分析（API 利用）               │
└──────────────────────────────────────────────────┘
              │
              ▼
       彼らが「打つ」
       あなたは黙って良い道具を作り続ける
```

## 52. 同モデルの先輩

| 組織 | 道具 | 「打つ」のは誰 |
|---|---|---|
| Signal Foundation | E2E メッセージ | ジャーナリスト・反体制派 |
| Tor Project | 匿名通信 | NGO・告発者 |
| OpenStreetMap | 地理データ | 災害支援・NPO |
| Wikimedia Foundation | Wiki | 編集者 |
| GitHub | コードホスト | 開発者・OSS |
| Internet Archive | アーカイブ | 歴史家・訴訟 |

→ 道具提供者は中立、利用者が政治化する。「**包丁屋は包丁を売る、料理人が料理を作る**」モデル。

## 53. 顔を出す場面 vs 出さない場面

### ✅ 出す
- 技術カンファレンス（エンジニア・OSS メンテナー）
- 学術学会（研究者・修論）
- 大学講演（技術解説）
- 自治体への提案・営業（ベンダー代表）
- メディア取材（**技術**面）
- 専門家証人（**技術**面）
- 国際会議（PDIS 等、日本 civic tech 代表）

### ❌ 出さない（他の人に渡す）
- 政府批判記者会見 → NPO・被害当事者
- 公共訴訟原告 → CALL4 + 当事者
- デモ・運動 → 既存運動団体
- 政治家ロビイング → 議員秘書・専門家団体
- TV ワイドショー → 出ない（最大の罠）
- Twitter/X 政府批判 → 最小限

## 54. 「裏で」する仕事

```
1. 障壁レポート公開（誰でも引用可、あなた個人は前に出ない）
2. 匿名化データ提供（ジャーナリスト記事化・研究者論文化・弁護士訴状）
3. 連名告発インフラ（PSI 技術提供、出すかは被害者連合判断）
4. 政策資料の作成支援（議員・NPO に技術的バックグラウンド）
5. メディアへの「証拠の問い合わせ先」（取材は他の人が受ける）
```

## 55. 中立性維持の仕組み

```
理事会（年 4 回、議事録公開）
  ├── あなた（代表）
  ├── 鈴木保志教授（学術）
  ├── 谷口律師（法律 / もし入ってくれれば）
  ├── 当事者代表 1 名（匿名可、任期 2 年）
  ├── DV NPO 代表 1 名
  └── 自治体経験者 1 名（退職者）

技術監査委員会（年 1 回、報告公開）
  → アルゴリズム・データの中立性確認

利益相反方針（公開）
  → 特定政党・特定企業との結託排除
  → 政府との契約は透明性報告書で開示

データガバナンス憲章（公開）
  → いかなる政府・企業も全件データへのアクセスは持たない
  → 研究目的の集計データのみ提供
```

## 56. 谷口律師面談（6 月第 1 週）の提案

```
「私は法律的に打つ役ではありません。
 ですが、打つ方々のための『証拠基盤と接続性』を作ります。
 谷口先生方が公共訴訟するとき、
 構造化された証拠・統計・連名告発インフラを
 オープンに提供したい。
 既存の CALL4 のミッションと**競合しない、補完する**。」
```

→ 谷口さんから見て「ライバル」ではなく「便利な道具を提供してくれる中立的な技術者」。
→ 関係が圧倒的に楽。

---

# 第 XII 部 — 結論と次のアクション

## 57. 3 つの現実シナリオ

```
シナリオ A（最良 15%）: 助成金 2 件採択 + 委託 2 件
  → 18 ヶ月で MVP + NPO 5 法人 + 学術論文 2 本
  → 修論 + 起業基盤
  → 5 年後: NPO 法人 + 100 法人連携 + 1-3 万 MAU

シナリオ B（標準 60%）: 助成金 1 件 + 委託 1 件 or 部分採択
  → 18 ヶ月で MVP + パイロット 2 法人 + 修論
  → 5 年後: 副業継続 + 学術発表多数 + 数万 MAU

シナリオ C（悲観 25%）: 助成金不採択、委託も不調
  → 18 ヶ月で修論完成、商業化なし
  → OSS 公開、海外研究者引用
  → あなたの被害は解決（ADR 結果次第）
  → 「やった経験」が次の機会の基盤
```

**いずれのシナリオでも**：
- ✅ 修論完成
- ✅ あなた個人の ADR 紛争解決経験
- ✅ OSS / データセット公開
- ✅ 日台産学ネットワーク構築

## 58. 次のアクション（優先順）

### 直近 1 週間
1. ✅ DB schema + 12 categories + 26 routing seed（完了）
2. ⏸️ 残り 7 categories の routing 詳細（特に sexual_violence、child_abuse — 命）
3. ⏸️ 配偶者暴力相談支援センター crawler
4. ⏸️ 緊急モード UI ワイヤーフレーム

### 直近 1 ヶ月
5. 谷口律師面談（6 月第 1 週）— **このレポート + Pillar 構造図 + 弁護士法 72 条議論**
6. ADR 仲裁第 1 回期日（あなたの製品欠陥案件）
7. 鈴木保志教授指導開始
8. IRB 申請準備
9. RISTEX SOLVE 2026 申請書ドラフト
10. SEO 12 本コア記事の最初の 3 本（DV / 製品欠陥 / admin_grievance）

### 直近 3 ヶ月
11. Web 問診 6 問 PWA
12. rule-based 推奨エンジン（LLM なし）
13. 4 つの主要 crawler（配暴セ・消費生活セ・児相・労基署）
14. パートナー 1-2 法人パイロット
15. こども家庭庁 SNS 相談事業（2026-04 公示予定）の提案書ドラフト

---

# 付録 A — DB スキーマ（投入済 12 problem_category）

```sql
INSERT INTO legalshield.problem_category VALUES
  ('dv',                  '配偶者・パートナー暴力（DV）',     critical, '#8008',           {gender,partner,urgent},  10),
  ('stalking',            'ストーカー被害',                   critical, '110',             {gender,partner,urgent},  20),
  ('sexual_violence',     '性犯罪・性暴力',                   critical, '#8891',           {gender,urgent},          30),
  ('child_abuse',         '児童虐待',                         critical, '189',             {child,urgent},           40),
  ('elder_abuse',         '高齢者虐待',                       high,     '地域包括支援セ',  {elder},                  50),
  ('school_bullying',     'いじめ・スクールハラスメント',     high,     '0120-0-78310',    {child,education},        60),
  ('workplace_harassment','職場ハラスメント',                 high,     '0570-919-471',    {workplace,labor},        70),
  ('labor_violation',     '労働基準法違反・賃金未払い',       high,     '0120-811-610',    {workplace,labor},        80),
  ('foreign_worker',      '外国人労働者の権利侵害',           high,     '0570-011000',     {workplace,foreign},      90),
  ('consumer_fraud',      '消費者被害・契約トラブル',         medium,   '188',             {consumer},              100),
  ('product_defect',      '製品欠陥・PL 被害',                high,     '188',             {consumer,tech},         110),
  ('admin_grievance',     '行政手続きの不利益',               high,     '0570-003-110',    {admin,family},          120);
```

---

# 付録 B — 議論ログのトピック索引

| 時刻 | トピック | 本書セクション |
|---|---|---|
| 17:43 | システム現状チェック | 1, 2 |
| 17:46 | 方針転換：問題種類 → NPO/行政 | 3, 4 |
| 17:49 | DB schema + seed 投入 | 2-3, 5 |
| 17:56 | weight = ベイズ prior 解説 | 5 |
| 18:01 | 入口設計 + 5 段同意 + 自殺境界 + 濫用防止 + 境界線図 | 7-14 |
| 18:11 | GIS スタック + 屋内測位 6 技術 | 24-25 |
| 18:17 | Lv0-Lv5 全シナリオマトリクス + ギャップ分析 | 15-23 |
| 18:24 | SEO + 5 段アクセス + コスト + 統合 + データセット | 27-31 |
| 18:32 | 6 軸 feasibility audit + 18 ヶ月 roadmap + 証拠基盤 + OSS leverage | 32-43 |
| 18:39 | 政府委託主軸の収入構造 | 44-50 |
| 18:43 | 官民協働 + アドボカシー hybrid（後に修正） | （初版） |
| 18:47 | プラットフォーム供給者モデルに収斂 | 51-56 |
| 18:50 | 本レポート | 全体 |

---

# 付録 C — 鈴木保志教授・谷口太規律師への 1 ページ要約

**プロジェクト名**：LegalShield — 困境分流プラットフォーム

**何を作る**：困境を抱える人が「**今、誰に、何を、どう伝えるか**」を 6 問で答える、加重付き法律分流プラットフォーム

**設計思想**：
1. **包丁屋になる**（料理人にはならない）
2. プラットフォームは「呼出までしかしない」、最終決定は人間
3. 5 段同意 ladder + 緊急時 bypass + 事後同意
4. 弁護士法 72 条境界の遵守（情報提供のみ）
5. オンデバイス SLM（プライバシー + コスト爆発回避）
6. 政府委託 + 研究助成 + 公益契約のハイブリッド収入

**ユニーク差分**：
- 製品欠陥被害当事者が ADR 進行中（**自分の体験を schema で validate**）
- 妻＝保健師の現場視点
- 台湾人配偶者の外国人視点
- 大学院 + 修論として論理化、撤回不能

**18 ヶ月のマイルストーン**：MVP 公開、自治体パイロット 2 件、論文 2 本、修論完成

**本日決定したこと**（2026-05-25）：
- 問題種類カテゴリ 12 + 加重 routing 26 ルートの DB 投入完了
- プラットフォーム供給者モデル採用（advocacy は他者に委ねる）
- 収入主軸を政府委託に確定（助成金は補助）

— Generated 2026-05-25 by 起案者 + Cascade —
