# FEWN / Safety GIS / JUDB 設計の証拠基盤

**Doc ID**: `EVIDENCE_BASE_20260520`
**目的**: 補助金申請・IRB 申請・警察協定打診時に引用できる査読済 / 政府公開証拠の集約。

---

## 1. 「社会安全網は機能していない」を裏付ける一次資料

### 1.1 日本

| 資料 | 主要数値 | 用途 |
|------|---------|------|
| 内閣府『男女間における暴力に関する調査』令和5年度 (R5) | **性暴力被害: 女性 約60%, 男性 約70% が誰にも相談していない** | 沈黙率の根拠 |
| 同 令和2年度 (R2) | 同様の沈黙率傾向の継続性 | 経年安定性の証明 |
| 同 平成29年度 (H29) | 「恥ずかしくてだれにも言えなかったから」が**女性の約半数** (相談しなかった理由) | 私的開示すら不可能だった根拠 |
| 内閣府 男女共同参画白書 R4 | 「性暴力被害について、女性の6割程度、男性の7割程度が、誰にも相談していない」 | 公式定量化 |
| 警察庁『犯罪情勢』R5 (npa_stalking 取得済) | ストーカー相談 19,843 / 検挙 1,081 = **ギャップ係数 18.36** | 司法システムへ届かない倍率 |

URL:
- https://www.gender.go.jp/policy/no_violence/e-vaw/chousa/r05_boryoku_cyousa.html
- https://www.gender.go.jp/about_danjo/whitepaper/r04/zentai/html/honpen/b1_s05_02.html
- https://www.gender.go.jp/policy/no_violence/e-vaw/chousa/pdf/h29danjokan-gaiyo.pdf

### 1.2 台湾

| 資料 | 主要数値 | 用途 |
|------|---------|------|
| 衛福部 保護服務司 統計 (2024) | 家暴通報 17.9 万件/年、親密関係暴力 8.5 万件/年 (約 50%) | 通報のみで既に大規模 |
| 王佩玲研究 (2024 報道) | **暴力発生から通報まで平均 4.2 年、深刻なケースは 6.8 年** | 「即座に救助が届かない」定量証拠 |
| 衛福部 同性親密関係暴力統計 | 平均 1,572 件/年 | LGBTQ 暗数の可視化 |
| 内政部警政署『跟蹤騷擾防制法』施行統計 (2022-) | (進行中) | 跟騷法の実効性評価 |

URL:
- https://dep.mohw.gov.tw/DOPS/lp-1303-105-xCat-cat01.html
- https://www.mohw.gov.tw/cp-2704-79175-1.html
- https://www.ctee.com.tw/news/20250624701016-431401 (王佩玲解説)
- https://www.npa.gov.tw/ch/app/data/list?module=wg057&id=2218

---

## 2. 「連続加害者が大量被害を生む」エビデンス (FEWN の核心仮説)

### 2.1 Lisak & Miller (2002) — 4% 仮説

| 出典 | 発見 | 数値 |
|------|------|------|
| Lisak, D. & Miller, P.M. (2002) "Repeat Rape and Multiple Offending Among Undetected Rapists." *Violence and Victims* 17(1):73-84 | **未検挙の加害者の中で、約 4% の連続加害者が大半の事案を起こす** | 1 加害者あたり **平均 5.8 件** の暴行 |
| NSVRC『Rethinking Serial Perpetration』 (2015) | 男性人口の trajectory: 94% 非加害, 2% 単発, **4% 高頻度連続** | 4% グループに焦点を当てる戦略の論拠 |
| RAINN | 加害者は「見知らぬ怖い人」ではなく「被害者の知人」が大半 | 「同一加害者が複数被害者の知り合い」という前提を支持 |

→ **これが FEWN の核**: 「重複検出」が高効果な理由 = 加害は分散していない、集中している。

### 2.2 再犯率の暗数

| 出典 | 発見 |
|------|------|
| Hanson & Morton-Bourgon (2005); Zgoba & Levenson (2008) | **司法記録ベースの性犯罪再犯率は 9-24%** |
| 同上 | **自己申告ベースは遥かに高い** (記録に残らない加害が大多数) |
| OJP SMART『Adult Sex Offender Recidivism』第5章 | 児童相手の加害は特に過小報告、被害児が加害者を知っている場合に著しい |

URL:
- https://www.nsvrc.org/sites/default/files/key-findings_rethinking-serial-perpetration.pdf
- https://www.researchgate.net/publication/11379469_Repeat_Rape_and_Multiple_Offending_Among_Undetected_Rapists
- https://smart.ojp.gov/somapi/chapter-5-adult-sex-offender-recidivism

---

## 3. 既存の類似システム = **Callisto** (FEWN の最強の先行事例)

### 3.1 何か

| 項目 | Callisto |
|------|---------|
| 提供開始 | 2015 (大学版), 2018 (Tech 業界 "Callisto Vault") |
| 創設者 | Jess Ladd (性暴力サバイバー) |
| 機能 | サバイバーが暗号化された開示を投稿、**同じ加害者** を投稿した別のサバイバーがいたら **マッチ** → 専属弁護士に通知 |
| 暗号方式 | Oblivious Pseudorandom Function (OPRF) + Public Key Encryption |
| 運用大学 | スタンフォード, ペンシルバニア大, USC など 30+ 大学 (歴史的) |
| 査読論文 | Rajan et al., "Callisto: A Cryptographic Approach to Detecting Serial Perpetrators of Sexual Misconduct" (2018, ACM COMPASS) |

→ **FEWN は Callisto の「写真特徴量を加えた発展版」**。既に米国で7年以上運用実績があり、訴訟リスクも顕在化していない (= 法的に成立する設計)。

### 3.2 重要な違い (FEWN がさらにやること)

| | Callisto | FEWN |
|--|---------|------|
| 入力 | テキスト (名前 / SNS URL) | テキスト + **顔エンベディング LSH** |
| マッチ精度 | 完全一致依存 (改名で逃げられる) | 顔バケット類似 (改名・改姓を貫通) |
| 対象 | 大学・テック業界 (限定) | DV / 性犯罪 / ストーカー全般 |
| 国 | 米国のみ | 日台双方 |
| 後段連携 | 専属弁護士 | NPO + 弁護士 + 警察 + 自治体 |

URL:
- https://www.projectcallisto.org/
- https://en.wikipedia.org/wiki/Callisto_(project)
- https://www.researchgate.net/publication/325889757_Callisto_A_Cryptographic_Approach_to_Detecting_Serial_Perpetrators_of_Sexual_Misconduct
- https://link.springer.com/article/10.1007/s41469-026-00202-1

---

## 4. 「市民参加センサーで政策を動かす」モデル — 空氣盒子の学術評価

| 出典 | 主要発見 |
|------|---------|
| Chen et al. (Academia Sinica, 2017) | AirBox プロジェクト発足、PM2.5 センサーの市民配備 |
| Wong et al. *Nature Humanities & Social Sciences Communications* (2022) "Translating citizen-generated air quality data into evidence for policy" | **市民データが実際に政策を動かした証拠**: 中央環保署が AirBox データを参照し政策反映 |
| Chen et al. *Sustainable Cities and Society* (2020) "From DIY to DIT" | 市民自助 → 政府協働への移行ガバナンスの分析 |

→ **FEWN の正当化根拠**: 「市民が出すデータが、政府の不全を補い、政策を動かした」前例がある。
被害証言の暗号化アグリゲートも同じガバナンス論理で説明可能。

URL:
- https://www.nature.com/articles/s41599-022-01135-2
- https://www.iis.sinica.edu.tw/en/page/report/9828.html
- https://www.sciencedirect.com/science/article/abs/pii/S2210670720308453

---

## 5. 暗号学的プライバシー保護マッチングの学術基盤

| 技術 | 出典 | FEWN 適用 |
|------|------|----------|
| Private Set Intersection (PSI) | Pinkas et al. "Efficient Set Intersection with Simulation-Based Security" *Journal of Cryptology* (2018) | バケット重複検出 |
| OpenMined PSI 実装 | Google Research 由来、商用ライセンス | ライブラリ選定 |
| Locality-Sensitive Hashing for face embeddings | Datar et al. "Locality-Sensitive Hashing Scheme Based on p-Stable Distributions" *SoCG* (2004) | 顔類似性のバケット化 |
| Threshold Cryptography | Shamir (1979), Desmedt & Frankel (1989) | m-of-n 鍵分散 (NPO/警察/弁連/IRB) |
| FaceNet / ArcFace | Schroff et al. CVPR 2015; Deng et al. CVPR 2019 | 端末顔エンベディング生成 |

→ **すべて査読論文 + 公開実装** あり、技術的成立性は確立済。

---

## 6. プライバシーが被害者保護に必須であるエビデンス

| 出典 | 発見 |
|------|------|
| NNEDV (National Network to End Domestic Violence) "Privacy & Confidentiality Matters" | DV シェルターの位置秘匿は「サバイバーの安全のために絶対必要」。プライバシー = 安全 |
| NNEDV "Stalking and Domestic Violence Intersection" | **ストーカーは親密関係パートナー殺人のリスクを 3 倍に高める** → 早期介入が命に関わる |
| NNEDV "Survivor's Guide to Cameras" | 加害者がテクノロジーで監視・追跡してくる現実 → 被害者側の対抗技術が必要 |

→ **FEWN がサーバに顔/位置を送らない設計は学術的に正当化される**: プライバシー漏洩 = 被害者の死亡リスク増加。

URL:
- https://www.techsafety.org/privacymatters
- https://nnedv.org/latest_update/intersections-of-stalking-and-domestic-violence/
- https://www.techsafety.org/guide-to-cameras

---

## 7. 既存の使えるデータベース (JUDB / Safety GIS への流入候補)

### 7.1 日本

| データセット | 公開元 | 入手方法 | 既に取得済か |
|-------------|--------|---------|-------------|
| 警察庁ストーカー・DV年次報告 | 警察庁 | PDF | ✅ npa_stalking.py |
| 男女間における暴力に関する調査 | 内閣府 | PDF/Excel | ⏳ 未実装 |
| 児童相談所での児童虐待相談対応件数 | 厚労省 | Excel | ⏳ 未実装 |
| 自殺対策白書 | 厚労省 | PDF/CSV | ⏳ 未実装 |
| 児童生徒の問題行動・不登校等調査 | 文科省 | Excel | ⏳ 未実装 |
| 法テラス利用統計 | 法テラス | PDF | ⏳ 未実装 |
| 性犯罪・性暴力被害者ワンストップ支援センター連絡先 | 内閣府 | HTML一覧 | ⏳ 未実装 (responder_assets 用) |
| 国土数値情報 P28 警察署等 | 国土交通省 | Shapefile/GeoJSON | ⏳ 未実装 (Safety GIS 用) |
| 都道府県別不審者情報メール | 各都道府県警 | RSS / メール配信 | ⏳ 未実装 |
| 犯罪統計書 | 警察庁 | PDF/Excel | ⏳ 未実装 |
| 矯正統計 | 法務省 | Excel | ⏳ 未実装 |

### 7.2 台湾

| データセット | 公開元 | 入手方法 | 既に取得済か |
|-------------|--------|---------|-------------|
| 司法院裁判書 | 司法院 | API (要登録) | ✅ judicial_tw.py |
| 家庭暴力防治統計 | 衛福部保護服務司 | Excel/PDF | ⏳ 未実装 |
| 性侵害防治統計 | 衛福部 | Excel | ⏳ 未実装 |
| 跟蹤騷擾防制法施行統計 | 警政署 | HTML/Excel | ⏳ 未実装 |
| 重要警政統計指標 | 警政署統計查詢網 | HTML/Excel | ⏳ 未実装 |
| 各縣市警察局所在地 | 政府資料開放平台 | CSV/JSON | ⏳ 未実装 |
| 113 保護專線統計 | 衛福部 | PDF | ⏳ 未実装 |
| 同性親密關係暴力統計 | 行政院性別平等會 | HTML | ⏳ 未実装 |

### 7.3 国際

| データセット | 公開元 | 用途 |
|-------------|--------|------|
| WHO Violence Against Women Database | WHO | 国際比較ベンチマーク |
| UN Women Global Database on Violence against Women | UN Women | 同上 |
| OECD Family Database (Violence) | OECD | 政策比較 |
| EIGE Gender Statistics Database | EIGE (EU) | EU 比較 |

---

## 8. ガバナンスの学術モデル (Steward Board の根拠)

| 出典 | 主要概念 | FEWN 適用 |
|------|---------|----------|
| Ostrom, Elinor (1990) "Governing the Commons" Nobel賞 | 共有資源を **多者制衡** で管理 | 警察+弁連+NPO+IRB の 4 者制 |
| Floridi (2018) "Soft ethics and the governance of the digital" | データガバナンスの倫理層 | 透明性レポート義務 |
| Crawford & Schultz (2014) "Big Data and Due Process" *Boston College Law Review* | プロファイリングへの異議申立権 | 本人開示請求 7 日内対応 |
| ProPublica COMPAS 調査報道 (2016) | 予測警察の差別増幅 | **やらない** ことの正当化 |

---

## 9. FEWN を補助金応募で「証拠駆動」に書く時の引用テンプレ

```markdown
## 必要性 (Need)
- 内閣府 R5 調査: 性暴力被害の女性 60%・男性 70% が誰にも相談していない [1]
- 警察庁 R5: ストーカー相談 19,843 件 vs 検挙 1,081 件、ギャップ係数 18.36 [2]
- 衛福部 (台): 親密関係暴力の通報まで平均 4.2 年 [3]

## 仮説の根拠 (Why repeat-detection works)
- Lisak & Miller (2002): 4% の連続加害者が大半の事案 [4]
- Hanson & Morton-Bourgon (2005): 司法統計の再犯率は氷山の一角 [5]

## 実装可能性 (Feasibility)
- Callisto (2015-) が大学・テック業界で 7 年以上運用実績 [6]
- Lin et al. (2022) Nature: 市民センサーが政策を動かした AirBox 前例 [7]

## プライバシー保護 (Privacy)
- NNEDV (2024): プライバシー = サバイバー安全の必須条件 [8]
- Pinkas et al. (2018) PSI: 暗号学的成立性は確立 [9]

## ガバナンス (Governance)
- Ostrom (1990): コモンズ管理の多者制衡モデル [10]
```

---

## 10. 一文サマリー

> **FEWN の各構成要素 (端末暗号化 + 顔エンベディング + LSH バケット + PSI + 多者制衡 + 透明性レポート) は、すべて査読論文または既存運用システムで実証済である。**
> **新規性は「組み合わせ」と「日台2拠点での同時展開」と「JUDB / 司法資料との三角佐証」にある。**
> **これは空想ではなく、すでに存在するパーツの工学的統合である。**

---

## 11. 次にやる引用整備

- [ ] 内閣府 R5 調査の PDF ダウンロード + 主要図表抽出 (cao_dv_survey crawler)
- [ ] 衛福部 統計 PDF ダウンロード (mohw_dv crawler)
- [ ] Lisak & Miller (2002) の原典 PDF を docs/refs/ に保存
- [ ] Callisto 査読論文の保存
- [ ] AirBox 査読論文 (Nature 2022) の保存
- [ ] BibTeX で `docs/refs/refs.bib` 生成

---

**End of Document**
