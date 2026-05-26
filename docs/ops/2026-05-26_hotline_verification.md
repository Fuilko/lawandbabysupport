# Hotline 番号 一括検証ノート（v1）

**作成日**: 2026-05-26
**目的**: `problem_category.urgent_hotline` 全 12 件と `category_routing` 内で参照される 24h hotline の正確性を出典付きで記録する。
**運用**: 月 1 回（または番号変更の報道があった時）見直す。

---

## 検証手順

1. 内閣府／厚労省／消費者庁／法務省など、所管省庁の公式ページで番号を確認。
2. 番号の **受付時間／対象** を控える（24h なのか平日昼のみなのか）。
3. ベンチマークとして、Google で「{機関名} 電話」検索の上位 3 件を crosscheck。
4. 食い違いがあれば、所管省庁ページ > 公益法人ページ > 報道 の順で優先。

---

## 全 12 categories の urgent_hotline

| code | 番号 | 機関 | 24h? | 出典 | 最終確認 |
|---|---|---|---|---|---|
| dv | **#8008**（はれれば） | DV 相談ナビ（内閣府） | 平日昼＋一部夜間 | gender.go.jp/policy/no_violence/e-vaw/soudankikan/01.html | 2026-05-26 OK |
| dv | **0120-279-889**（つなぐはやく） | DV 相談＋（24h） | **24h** | dv-soudanplus.jp | 2026-05-26 OK ※追加検討 |
| stalking | **110** | 警察 | 24h | npa.go.jp | 2026-05-26 OK |
| stalking | **#9110** | 警察相談専用 | 平日 8:30-17:15 | npa.go.jp | 2026-05-26 OK |
| sexual_violence | **#8891**（はやくワンストップ） | 性犯罪・性暴力被害者ワンストップ支援センター | 24h（地域差あり） | gender.go.jp/policy/no_violence/seibouryoku/consult.html | 2026-05-26 OK |
| sexual_violence | **#8103**（ハートさん） | 警察 性犯罪被害相談電話 | 24h | npa.go.jp | 2026-05-26 OK |
| child_abuse | **189**（いちはやく） | 児童相談所虐待対応ダイヤル | 24h | mhlw.go.jp/189/ | 2026-05-26 OK |
| elder_abuse | **地域包括支援センター**（市区町村ごと番号異なる） | 地域包括 | 平日昼 | mhlw.go.jp | 2026-05-26 番号は固定でない |
| school_bullying | **0120-0-78310**（なやみ言おう） | 24 時間子供 SOS ダイヤル（文科省） | 24h | mext.go.jp | 2026-05-26 OK |
| school_bullying | **0120-99-7777** | チャイルドライン（18 歳まで） | 月-土 16-21 時 | childline.or.jp | 2026-05-26 OK |
| workplace_harassment | **0570-919-471** | 総合労働相談コーナー（厚労省） | 平日昼 | mhlw.go.jp/general/seido/chihou/kaiketu/soudan.html | 2026-05-26 OK |
| workplace_harassment | **0120-714-864** | ハラスメント悩み相談室（厚労省委託） | 平日昼＋一部 | no-harassment.mhlw.go.jp | 2026-05-26 OK |
| labor_violation | **0120-811-610**（はい労働） | 労働条件相談ほっとライン（厚労省） | 平日夜＋土日祝 | check-roudou.mhlw.go.jp | 2026-05-26 OK |
| foreign_worker | **0570-011000** | 外国人労働者向け相談ダイヤル | 平日昼 | mhlw.go.jp/stf/seisakunitsuite/bunya/0000216213.html | 2026-05-26 OK |
| consumer_fraud | **188**（いやや） | 消費者ホットライン | 平日昼＋土日（一部） | caa.go.jp | 2026-05-26 OK |
| product_defect | **188** | 消費者ホットライン | 同上 | caa.go.jp | 2026-05-26 OK |
| admin_grievance | **0570-003-110** | みんなの人権 110 番（法務省） | 平日 8:30-17:15 | moj.go.jp/JINKEN/jinken20.html | 2026-05-26 OK |

---

## ToDo

- [ ] **DV 相談＋ 0120-279-889** を `category_routing` に T1 として追加検討（#8008 は 24h ではないため）。
- [ ] **#9110** が 24h でないこと、`urgent_hotline` 表示の際に注釈を付ける。
- [ ] **elder_abuse** は番号固定でないため、API 側で「お住まいの市区町村の地域包括支援センターへ」と表示し、市町村検索リンクを併置するロジックが必要。
- [ ] **#8891** の地域差（東京 24h、地方は平日昼のみ等）を `notes_ja` に明記する。
- [ ] 各 hotline の `accepts: ["ja", "en", "zh", "ko", ...]` 多言語対応マトリクスを集約する。

## 番号変更が起きうるリスク

| カテゴリ | 変更可能性 | 対応 |
|---|---|---|
| 短縮ダイヤル（#8008, #8891, 189, 188 等） | 低（総務省割当） | 年 1 回確認 |
| 0570 ナビダイヤル | 中（事業者変更） | 半年確認 |
| 各都道府県の福祉事務所 0XXX-XX-XXXX | 高（部署改編で変わる） | 内閣府 PDF crawl で月次同期 |

## 自動再検証

`gis/ingest/ingest_dv_centers.py` のように、内閣府／厚労省／消費者庁の公式 PDF/HTML を月次クロールするバッチを追加予定（DV: 既存／その他 11 カテゴリ: 未実装）。
