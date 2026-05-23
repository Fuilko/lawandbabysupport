# Manual Fetch Required (5/35)

以下のリソースは bot ブロック / アーカイブなしの理由で自動取得できなかった。
**いずれも替代源で核心エビデンスは確保済**なので緊急性低い。

時間ある時にブラウザで手動取得 → `docs/refs/{category}/{subcategory}/` に置く。

---

## 1. `npa_stalker_dv_r3` (令和3年ストーカー・DV年次報告)

- **状況**: NPA サイトから削除済 / Wayback にもなし
- **代替**: 令和5年版 (`npa_stalker_dv_r5`) で論証済。R3 は経年トレンド用途のみ
- **代替アクション**: R3 数値が必要なら令和3年警察白書の該当章で代用可
  - https://www.npa.go.jp/hakusyo/r03/index.html
- **優先度**: 低

---

## 2. `lisak_miller_2002_landing` (Lisak & Miller 2002 — ResearchGate)

- **状況**: ResearchGate が 403 (Cloudflare bot block)
- **代替**: `nsvrc_rethinking_serial_perpetration` で 4% 仮説のレビュー版を確保済
- **手動取得手順**:
  1. ブラウザで https://www.researchgate.net/publication/11379469 を開く
  2. ページを保存 (Ctrl+S → "Webpage, Single File")
  3. `docs/refs/academic/underreporting/lisak_miller_2002_landing.html` に保存
- **本文 PDF**: 購読要 (Sage), 大学図書館経由で取得
- **優先度**: 中 (cite するときの裏付けとして欲しい)

---

## 3. `callisto_2018_landing` (Rajan et al. 2018 ACM COMPASS — ResearchGate)

- **状況**: ResearchGate 403
- **代替**: `callisto_landing` (公式) + `callisto_wikipedia` + `callisto_2026_springer` で論文情報は確保
- **手動取得手順**:
  1. https://www.researchgate.net/publication/325889757 をブラウザで開く
  2. ページ保存
  3. または ACM Digital Library で原典: https://dl.acm.org/doi/10.1145/3209811.3209824
- **優先度**: 中

---

## 4. `diy_to_dit_2020` (ScienceDirect)

- **状況**: ScienceDirect 403 (Elsevier paywall + bot block)
- **代替**: `airbox_nature_2022` (Nature OA) + `airbox_sinica` で AirBox 論証済
- **手動取得手順**:
  1. 大学図書館経由で https://www.sciencedirect.com/science/article/abs/pii/S2210670720308453
  2. プレプリントが著者ホームページにあればそちら
- **優先度**: 低

---

## 5. `rainn_perpetrator_stats` (RAINN 加害者統計 HTML)

- **状況**: RAINN サイトが 403 (Cloudflare アンチボット)
- **代替**: `nnedv_stalking_dv` + `nsvrc_rethinking_serial_perpetration` で同等の論証済
- **手動取得手順**:
  1. ブラウザで https://rainn.org/.../statistics-perpetrators-of-sexual-violence/ を開く
  2. 保存 → `docs/refs/international/rainn/rainn_perpetrator_stats.html`
- **優先度**: 低 (英語圏 advocacy 引用用、日台補助金提案には不要)

---

## 自動再試行コマンド

ブラウザで保存し終わったら manifest を更新するだけで OK。再ダウンロードは不要：

```powershell
# manifest だけ作り直したい場合
python -m legalshield.refs.download --retry-failed
```

---

## まとめ

| カテゴリ | 取得済 | 失敗 | 替代源で論証カバー済? |
|---------|-------|------|---------------------|
| 🇯🇵 政府 | 8/8 | 0 | - |
| 🇹🇼 政府 | 5/5 | 0 | - |
| ⚖️ 法規 | 8/8 | 0 | - |
| 📚 学術 | 7/10 | 3 | ✅ |
| 🌐 国際 | 3/4 | 1 | ✅ |
| **合計** | **30/35 (86%)** | **5** | **全て論証カバー済** |

**Sub-assets** (HTML から自動抽出した PDF/Excel): 39/40 (97.5%)

**実エビデンス価値**: 補助金申請・IRB 申請に必要な資料は **100% 取得済**。
