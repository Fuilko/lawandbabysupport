# LegalShield Project Timeline

> **Past → Present → Future**
> 
> 開発ノート: 本プロジェクトは個人の実体験（¥6,800万企業不正事件）から生まれた社会課題解決型 Civic Tech です。
>
> **Language**: [🇯🇵 Japanese below] · [🇺🇸 English below] · [🇹🇼 繁體中文 below]

---

## 🇯🇵 日本語

### 過去（ catalyst → concept ）

| 日付 | イベント | 詳細 |
|------|---------|------|
| 2026-02-03 | Mapry M4-0 ドローン重大事故 | 台湾・新竹県で製品欠陥による飛行事故。製造元の不正対応を契機に、法制度・企業倫理の問題を深く認識。 |
| 2026-02~03 | フォレンジック調査 | 57GBシステムログ解析、34項目の安全欠陥発見、ADR（裁判外紛争解決）申立準備。 |
| 2026-04-28 | SDカード完全抽出 | 108ファイルの全証拠抽出、DJI由来・ROS1→ROS2不完全移行等の決定的欠陥発見。 |
| 2026-04 | 概念誕生 | 「デジタル賦権（Digital Empowerment）」— 個人の訴訟経験から、被害者支援システムの構想を開始。 |
| 2026-05-04 | プロダクト計画書作成 | [PRODUCT_PLAN.md](./PRODUCT_PLAN.md) — LegalShield（法盾）+ PocketMidwife（口袋助産士）の二本柱構想。 |

### 現在（ development → validation ）

| 日付 | イベント | 詳細 |
|------|---------|------|
| 2026-05-05 | POC v1 | 初期概念検証：判例ベクトル化の実験開始。 |
| 2026-05-06 | POC v2~v3 | LanceDB 導入、71,054件判例・724,443チャンクの埋め込み完了（RTX 4080、38分）。 |
| 2026-05-07 | POC v4 + セットアップ完了 | RAG検索パイプライン稼働、Ollama連携（phi4:14b / gemma3:27b / llama3.3:70b）。 |
| 2026-05-08~10 | 多言語紹介ページ | JP/ZH/EN 三語 HTML 作成、言語切替機能実装。 |
| 2026-05-11 | 開発者ストーリー刷新 | 「反乱宣言（Declaration of Uprising）」— 業界プロジェクト破壊→社会安全網誕生の叙事。 |
| 2026-05-12 | Toyota Foundation 提案書 | 共同研究助成申請（¥800万、2年間）。**実証研究（Empirical Research）** として再定義。 |
| 2026-05-13~14 | 技術・予算精緻化 | LLM/SLM ハイブリッド + RAG、96GB+ RAM GPU ワークステーション、予算数学修正。 |

**現在の技術的到達点：**
- 日本国法 623,000 件 + 判例 724,443 件のベクトル化
- SLM（Phi-3 / Qwen2.5 / Gemma 3B~14B 量子化）+ LLM（70Bクラス）ハイブリッド
- RAG（検索拡張生成）— ハルシネーション抑制・法源強制引用
- 17類型犯罪分類 + 加害者プロファイリング
- 証拠金庫（SHA256 + NTPタイムスタンプ + Audit Log）
- 被害届不受理防止機能（日本初）

### 未来（ deployment → impact ）

| 時期 | フェーズ | 目標 |
|------|---------|------|
| 2026-06~10 | 準備期 | Flutter プロトタイプ、AI 5ロール統合、NPOパートナー調整（DV支援センター・児童相談所・弁護士会） |
| 2026-11 | 助成開始（目標） | 高知県パイロット運営開始（50名被害者・支援者）。LLM/SLM 本格稼働。57GB Mapry 証拠データストレステスト。 |
| 2027-02 | 全国β版 | 17類型全対応、民事・行政法分野拡張。全国公開β版リリース。 |
| 2027-05 | 中間報告① | PoC 成果データ集計、NPO フィードバック統合、SLM v2.0 リリース。 |
| 2027-08 | SaaS 開発 | 自治体・企業向け GovTech SaaS 開発開始。匿名化統計ダッシュボードβ版。 |
| 2027-11 | 中間報告② | 学術論文投稿（AI法推論・被害者UX）、台湾・日台連携拡大。 |
| 2028-02 | 全国展開 | 弁護士会・NPO・自治体 10 都市以上。多言語展開（繁體中文・英語）準備。 |
| 2028-05 | 中間報告③ | 最終データ集計、政策提言書作成、ISO27001 資安認証取得。 |
| 2028-10 | 助成完了 | 「AI被害者支援システムの社会実装に関する実証研究報告書」+「社会影響力実際報告書」提出。 |
| 2028-11 | 最終成果物提出 | Toyota Foundation 規定フォーマットでの完了報告。 |
| 2028-12~ | 持続化・国際展開 | B2B2G 収益モデル本格稼働。台湾→東南アジア→多言語展開。 |

---

## 🇺🇸 English

### Past (Catalyst → Concept)

| Date | Event | Detail |
|------|-------|--------|
| 2026-02-03 | Mapry M4-0 drone crash | Taiwan Baxianshan. Major safety defect incident triggered deep awareness of corporate fraud and legal system gaps. |
| 2026-02~03 | Forensic investigation | 57GB system log analysis, 34 safety defects identified, ADR preparation. |
| 2026-04-28 | Full SD card extraction | 108 files extracted. DJI origin, ROS1→ROS2 incomplete migration, circular systemd dependencies discovered. |
| 2026-04 | Concept born | "Digital Empowerment" — born from personal litigation experience, began designing victim support system. |
| 2026-05-04 | Product plan | [PRODUCT_PLAN.md](./PRODUCT_PLAN.md) — Dual track: LegalShield + PocketMidwife. |

### Present (Development → Validation)

| Date | Event | Detail |
|------|-------|--------|
| 2026-05-05 | POC v1 | Initial concept validation: precedent vectorization experiment. |
| 2026-05-06 | POC v2~v3 | LanceDB adopted. 71,054 precedents + 724,443 chunks embedded (RTX 4080, 38 min). |
| 2026-05-07 | POC v4 + Setup complete | RAG query pipeline operational, Ollama integration (phi4:14b / gemma3:27b / llama3.3:70b). |
| 2026-05-08~10 | Trilingual intro pages | JP/ZH/EN HTML created with language switcher. |
| 2026-05-11 | Developer story revamp | "Declaration of Uprising" — industry project destroyed → social safety net born. |
| 2026-05-12 | Toyota Foundation proposal | Joint Research Grant application (¥8M, 2 years). Redefined as **Empirical Research**. |
| 2026-05-13~14 | Technical refinement | LLM/SLM hybrid + RAG, 96GB+ RAM GPU workstation spec, budget math corrected to exact ¥8M. |

**Current technical milestones:**
- 623,000 Japanese laws + 724,443 precedents vectorized
- SLM (Phi-3 / Qwen2.5 / Gemma 3B~14B quantized) + LLM (70B-class) hybrid
- RAG (Retrieval-Augmented Generation) with forced legal source citation
- 17 crime types + perpetrator profiler
- Evidence vault (SHA256 + NTP timestamp + Audit Log)
- Anti-grafting police report feature (first in Japan)

### Future (Deployment → Impact)

| Period | Phase | Goal |
|--------|-------|------|
| 2026-06~10 | Preparation | Flutter prototype, AI 5-role integration, NPO partner alignment. |
| 2026-11 | Grant start (target) | Kochi pilot launch (50 victims/supporters). Full LLM/SLM operation. 57GB Mapry stress test. |
| 2027-02 | National beta | All 17 types + civil/administrative law. National beta release. |
| 2027-05 | Mid-term report #1 | PoC data aggregation, NPO feedback integration, SLM v2.0 release. |
| 2027-08 | SaaS development | GovTech SaaS for municipalities/enterprises. Anonymized stats dashboard beta. |
| 2027-11 | Mid-term report #2 | Academic paper submission (AI legal inference, victim UX), Taiwan collaboration expansion. |
| 2028-02 | National expansion | 10+ cities (bar associations, NPOs, municipalities). Multilingual prep (Traditional Chinese, English). |
| 2028-05 | Mid-term report #3 | Final data aggregation, policy recommendation, ISO27001 certification. |
| 2028-10 | Grant completion | "Empirical Research Report on AI Victim Support System" + "Social Impact Report" submitted. |
| 2028-11 | Final deliverables | Completion report per Toyota Foundation format. |
| 2028-12~ | Sustainability & global | Full B2B2G revenue model. Taiwan → Southeast Asia → multilingual expansion. |

---

## 🇹🇼 繁體中文

### 過去（催化 → 概念）

| 日期 | 事件 | 詳情 |
|------|------|------|
| 2026-02-03 | Mapry M4-0 無人機重大事故 | 台灣新竹縣，產品缺陷導致飛行事故。製造商的不正當處理促使深刻認識法律制度與企業倫理問題。 |
| 2026-02~03 | 鑑識調查 | 57GB 系統日誌解析，發現 34 項安全缺陷，準備 ADR（裁判外紛爭解決）申請。 |
| 2026-04-28 | SD 卡完全提取 | 108 個文件全數提取，發現 DJI 來源、ROS1→ROS2 不完全遷移等決定性缺陷。 |
| 2026-04 | 概念誕生 | 「數位賦權（Digital Empowerment）」— 從個人訴訟經驗出發，開始構想被害者支援系統。 |
| 2026-05-04 | 產品計畫書 | [PRODUCT_PLAN.md](./PRODUCT_PLAN.md) — LegalShield（法盾）+ PocketMidwife（口袋助產士）雙軌構想。 |

### 現在（開發 → 驗證）

| 日期 | 事件 | 詳情 |
|------|------|------|
| 2026-05-05 | POC v1 | 初始概念驗證：判例向量化實驗開始。 |
| 2026-05-06 | POC v2~v3 | 導入 LanceDB，71,054 件判例、724,443 個區塊嵌入完成（RTX 4080，38 分鐘）。 |
| 2026-05-07 | POC v4 + 設定完成 | RAG 檢索管道運作，Ollama 連動（phi4:14b / gemma3:27b / llama3.3:70b）。 |
| 2026-05-08~10 | 多語言介紹頁 | 製作 JP/ZH/EN 三語 HTML，實作語言切換功能。 |
| 2026-05-11 | 開發者故事翻新 | 「反亂宣言（Declaration of Uprising）」— 業界計畫被摧毀→社會安全網誕生。 |
| 2026-05-12 | Toyota Foundation 提案書 | 共同研究助成申請（¥800 萬、2 年）。重新定義為**實證研究（Empirical Research）**。 |
| 2026-05-13~14 | 技術・預算精緻化 | LLM/SLM 混合 + RAG、96GB+ RAM GPU 工作站規格、預算數學修正。 |

**目前技術里程碑：**
- 日本國法 623,000 件 + 判例 724,443 件向量化
- SLM（Phi-3 / Qwen2.5 / Gemma 3B~14B 量化）+ LLM（70B 級）混合架構
- RAG（檢索擴增生成）— 強制引用法源、抑制幻覺
- 17 類型犯罪分類 + 加害者側寫
- 證據金庫（SHA256 + NTP 時間戳 + 稽核日誌）
- 被害申告不受理防止功能（日本首創）

### 未來（部署 → 影響力）

| 時期 | 階段 | 目標 |
|------|------|------|
| 2026-06~10 | 準備期 | Flutter 原型、AI 5 角色整合、NPO 夥伴協調（DV 支援中心・兒童諮商所・律師會） |
| 2026-11 | 助成開始（目標） | 高知縣試點營運（50 名被害者・支援者）。LLM/SLM 正式運作。57GB Mapry 證據壓力測試。 |
| 2027-02 | 全國 β 版 | 17 類型全對應、民事・行政法領域擴張。全國公開 β 版發布。 |
| 2027-05 | 中期報告① | PoC 成果資料彙整、NPO 意見回饋整合、SLM v2.0 發布。 |
| 2027-08 | SaaS 開發 | 自治體・企業向 GovTech SaaS 開發開始。匿名化統計儀表板 β 版。 |
| 2027-11 | 中期報告② | 學術論文投稿（AI 法推論・被害者 UX）、台灣・日台合作擴大。 |
| 2028-02 | 全國展開 | 律師會・NPO・自治體 10 都市以上。多語言展開（繁體中文・英語）準備。 |
| 2028-05 | 中期報告③ | 最終資料彙整、政策建議書作成、ISO27001 資安認證取得。 |
| 2028-10 | 助成完結 | 「AI 被害者支援系統之社會實裝實證研究報告書」+「社會影響力實際報告書」提交。 |
| 2028-11 | 最終成果物提交 | 依 Toyota Foundation 規定格式提交完結報告。 |
| 2028-12~ | 持續化・國際展開 | B2B2G 收益模式正式運作。台灣→東南亞→多語言展開。 |

---

## 開發者註記 Developer Notes

> **代表者**: 劉建志（リュウ・ケンジ / Kenji Liu）
> **所属**: 高知大学 大学院農学研究院 森林科学領域 / 光伊フォレスト株式会社
> **年齢**: 30 代（37歳）
> **拠点**: 高知県幡多郡
> **連絡**: info@legalshield.jp（公開用）

---

*Last updated: 2026-05-14*
