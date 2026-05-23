# 資料庫擴充 + NPO/律師/福祉協作派遣系統 設計

**作成日：** 2026年5月20日  
**範圍：** (Q1) 台灣資料儲存策略 / (Q2) 日本資料追加 / (Q3) GPS 就近通報 + 中央監控  
**對象：** 開發團隊 + 顧問律師 + 補助金審查（豐田財団等）

---

## Part A — Q1：台灣資料 1-200GB 估算與儲存策略

### A-1 容量分析（為什麼會到 200GB）

```
原始判決書：
  3,000 萬份 × 平均 5 KB（純文字 UTF-8）         = 150 GB
  + JSON metadata（案號/法院/日期/分類等）         + 30 GB
  + 附件（PDF 影本 / 表格圖）                     + 50-100 GB
  ────────────────────────────────────────
  原始下載量                                      ≈ 200-300 GB

Embedding（multilingual-e5-small, 384 dim, float32）：
  平均切 chunk = 每件 5-10 chunk
  每 chunk = 384 × 4 bytes = 1.5 KB（向量本體）
  + chunk text（500 字 ≈ 1.5 KB）+ metadata（0.5 KB）
  ≈ 3.5 KB / chunk
  3 億 chunk × 3.5 KB                            = 1 TB ← ⚠️ 失控

LanceDB 壓縮（IVF + PQ 8x）：
  PQ 8x 壓縮：1.5 KB → 0.2 KB
  → 3 億 chunk × ~2.2 KB                         ≈ 660 GB

→ 全量入庫 = 不現實
→ 必須分層 + 篩選
```

### A-2 推薦的「分層 + 主題化」策略

**不要全部入 LanceDB。分三層：**

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: HOT（向量搜尋）— 5-10 GB                       │
│  - LegalShield 任務直接相關 5-10 主題                    │
│  - 高等法院・最高法院・憲法法庭判決優先                    │
│  - 近 5 年（2020-2025）                                  │
│  - 估計：10-30 萬筆 chunk                                │
│  - 用於：即時 RAG retrieve                              │
├─────────────────────────────────────────────────────────┤
│  Layer 2: WARM（關鍵字搜尋）— 30-50 GB                   │
│  - 全主題、近 10 年                                      │
│  - 純文字 + SQLite/DuckDB FTS5 全文索引                 │
│  - 估計：500 萬筆全文                                    │
│  - 用於：精確查詢（案號、日期、條文編號）                 │
├─────────────────────────────────────────────────────────┤
│  Layer 3: COLD（離線歸檔）— 100-200 GB                   │
│  - 全量 ZIP 原檔                                         │
│  - 外接硬碟 / NAS / S3 Glacier                           │
│  - 用於：學術研究、按需分析                               │
└─────────────────────────────────────────────────────────┘
```

### A-3 主題篩選（Mapry 案 + LegalShield 任務優先）

| 優先 | 主題 | 對應任務 | 估件數 |
|------|------|---------|--------|
| 🔴 P0 | 政府採購法 第 101 條 不良廠商 | Mapry 案直接救命 | ~5,000 |
| 🔴 P0 | 代理商 / 經銷契約 損害賠償 | Mapry 案 | ~10,000 |
| 🔴 P0 | 跟蹤騷擾防制法（2022年起） | App 核心功能 | ~500 |
| 🔴 P0 | 性騷擾防治三法 | App 核心功能 | ~5,000 |
| 🟠 P1 | 兒少法 / 兒虐 | App 核心功能 | ~10,000 |
| 🟠 P1 | 家庭暴力防治法 | App 核心功能 | ~30,000 |
| 🟠 P1 | 個資法 | 開發者保護 | ~3,000 |
| 🟠 P1 | 物之瑕疵 / 不完全給付 | Mapry 案 | ~20,000 |
| 🟡 P2 | 詐欺民事 / 刑事 | Mapry + 一般用戶 | ~50,000 |
| 🟡 P2 | 妨害名譽 / 誹謗 | 開發者保護 | ~30,000 |
| 🟡 P2 | 妨害秘密（偷拍） | App 核心功能 | ~3,000 |

**P0+P1 = ~83,500 件 ≈ 5-10 GB（含 embedding）→ 完全可入 LanceDB**

### A-4 PQ 量化壓縮設定

```python
# LanceDB 寫入時用 IVF-PQ
import lancedb
db = lancedb.connect("D:/projects/LegalShield/lancedb")

table = db.create_table(
    "tw_precedents",
    schema=schema,
    mode="create",
)
# 索引時 PQ 壓縮
table.create_index(
    metric="cosine",
    num_partitions=256,         # IVF 分片
    num_sub_vectors=96,         # PQ 子向量數（384/96=4 dims/sub）
    accelerator="cuda",         # RTX 4080 加速
)
# 結果：1.5 KB embedding → ~96 bytes（壓縮 16x）
# 精度損失：通常 ~3-5% recall，對 RAG 可接受
```

---

## Part B — Q2：日本資料追加（佐證開發必要性）

### B-1 為什麼需要追加：「資料稀少 → 必要性論證困難」

豐田財団 / 學術 IRB / 補助金 審查人員的邏輯：

```
你想做：被害者支援 App
   ↓ 第一個問題
「日本有多少人需要這個？官方數據？」
   ↓
你只能拿出：警察犯罪統計總表（粗）
   ↓ 第二個問題
「報案率多少？實際被害數估計？求助失敗的數據？」
   ↓
日本官方資料：稀薄、零散、隱藏
   ↓ 結論
「データに基づく必要性の根拠が弱い」→ 採点低い
```

**對策：建立「Japan Underreporting Database」(JUDB)** — 把日本散落的「求助失敗」「暗數」「被害但未通報」資料集中。

### B-2 「求助無門」的資料源（已驗證）

#### 警察 / 刑事系統的暗數

| 來源 | URL | 量級 | 備考 |
|------|-----|------|------|
| 警察庁 犯罪統計（月次・年次） | https://www.npa.go.jp/publications/statistics/ | 月次 PDF + Excel | 已部分有 npa_scraper |
| 警察庁 ストーカー相談件数 | 年次資料 | ~2 万件/年 | **vs 検挙数 → gap = 暗數** |
| 警察庁 配偶者暴力相談件数 | 年次 | ~9 万件/年 | 同上 |
| 警察庁 児童ポルノ事件統計 | 年次 | 検挙数のみ | 被害児童の其後追跡なし |
| 検察庁 統計年報 | https://www.kensatsu.go.jp/kakuchou/syouri/ | PDF/Excel | 起訴率 / 不起訴理由 |
| 法務総合研究所 犯罪白書 | https://www.moj.go.jp/housouken/ | PDF 年次 | 解説 + 統計 |
| 法務省 矯正統計 | https://www.moj.go.jp/housei/toukei/ | 年次 | 受刑者・少年院 |

#### 行政・福祉系統（被害者其後）

| 來源 | URL | 量級 | 用途 |
|------|-----|------|------|
| 内閣府 男女共同参画局 DV 統計 | https://www.gender.go.jp/policy/no_violence/ | 年次 | DV 相談 vs 警察介入 |
| 内閣府 性犯罪・性暴力ワンストップ支援センター | https://www.gender.go.jp/policy/no_violence/seibouryoku/ | 年次 件数 | **47 都道府県で件数大差 = 偏在** |
| 厚労省 児童相談所 相談対応件数 | https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000122802.html | 年次 | 一時保護率の都道府県差 |
| 厚労省 福祉行政報告例 | e-Stat | 月次・年次 | 児童虐待・家庭支援 |
| 厚労省 自殺対策白書 | 年次 | 年次 | 被害類型別自殺率 |
| 文科省 いじめ・暴力・不登校 調査 | 年次 | 全国学校別 | 児童暴力暗數 |
| 法テラス 利用統計 | https://www.houterasu.or.jp/ | 年次 | **法律扶助の地理的偏在** |

#### 「相談しなかった理由」アンケート（重要！這是「求助無門」直接證據）

| 來源 | 內容 |
|------|------|
| 内閣府「男女間における暴力に関する調査」（3 年毎） | DV/性暴力 被害者で「相談しなかった」割合・理由 |
| 内閣府「子供・若者白書」 | 子供の SOS 出さなかった理由 |
| 厚労省「子供の生活状況調査」 | 困難 vs 行政接続率 |
| 警察庁「犯罪被害類型別調査」 | 被害類型別の通報率 |

**這些調查是金礦** — 直接證明「日本被害者求助率低 + 求助系統有缺口」。

#### 民間 / 学術系（補強）

| 來源 | 用途 |
|------|------|
| NPO「ぱっぷす」https://www.paps.jp/ | 性暴力被害者支援 — 公開データ |
| 「全国女性シェルターネット」https://nwsnet.or.jp/ | 全国シェルター利用統計 |
| 「Lifelink」https://lifelink.or.jp/ | 自殺対策統計 |
| 国立社会保障・人口問題研究所 | 大規模調查 |
| 学術 J-STAGE 論文（已有 jstage_analyzer.py） | 学術文献 |
| 各都道府県 性暴力支援センター 年報 | 47 件の地域差 |

#### 媒體 / その他

| 來源 | 用途 |
|------|------|
| 朝日 / 毎日 / NHK 過去記事 DB（学術引用 OK） | 個別事件のフォロー |
| 国会議事録 | 国会での発言・質問 |
| 司法統計年報（最高裁） | 民事・刑事件数 |

### B-3 推薦追加爬蟲（要寫的 Python 模組）

```
legalshield/crawlers/jp_underreporting/
├── npa_stalking.py             # 警察庁 ストーカー
├── npa_dv.py                   # 警察庁 配偶者暴力
├── moj_crime_white.py          # 犯罪白書 PDF
├── kensatsu_stats.py           # 検察庁 統計年報
├── cao_dv_survey.py            # 内閣府 男女間暴力調査
├── cao_youth.py                # 内閣府 子供若者白書
├── mhlw_jido_soudan.py         # 厚労省 児童相談所
├── mhlw_suicide.py             # 厚労省 自殺白書
├── mext_ijime.py               # 文科省 いじめ調査
├── houterasu_stats.py          # 法テラス 統計
├── npos_aggregate.py           # NPO 連合データ
├── pref_support_centers.py     # 47 都道府県 支援センター年報
└── academic_jstage.py          # 既存 jstage_analyzer の被害者支援テーマ拡張
```

### B-4 「Japan Underreporting Database」(JUDB) 設計

```sql
-- 一張統合表，做時序 + 地理 + 類型分析
CREATE TABLE jp_underreporting (
    id              UUID PRIMARY KEY,
    source          TEXT,         -- 警察庁・内閣府・厚労省・NPO...
    source_url      TEXT,
    publish_date    DATE,
    period_start    DATE,
    period_end      DATE,
    
    -- 地理
    prefecture      TEXT,         -- 47 都道府県 or "全国"
    municipality    TEXT,         -- 市区町村（あれば）
    
    -- 分類
    crime_type      TEXT,         -- DV / ストーカー / 性暴力 / 児童虐待 ...
    victim_type     TEXT,         -- 女性 / 男性 / 子供 / LGBT ...
    
    -- 数値
    metric_name     TEXT,         -- 「相談件数」「検挙件数」「不起訴率」「自殺数」...
    metric_value    NUMERIC,
    metric_unit     TEXT,
    
    -- メタ
    raw_text        TEXT,         -- 出所原文
    notes           TEXT,
    embedding       VECTOR(384)   -- 検索用
);

-- これで以下の「求助無門」証拠が一発で出る：
-- ① 都道府県別の支援センター件数のばらつき（標準偏差）
-- ② DV 相談件数 ÷ 検挙件数 = ギャップ係数（地域別）
-- ③ 「相談しなかった割合」の経年変化
-- ④ 児相一時保護率の地域差
-- ⑤ 法テラス 1 万人あたり利用率の偏在
```

### B-5 必要性論証の「3 つのキラー指標」

豐田財団 / 學術審查 直接打中三個指標：

```
【キラー指標 1】「ギャップ係数」
   = 相談件数 ÷ 検挙件数
   DV 相談 9 万件 / 検挙 8 千件 → ギャップ係数 ~11
   → 90% 以上が刑事処分に至らない → 「求助しても助けられない」証明

【キラー指標 2】「地域偏在係数」
   = 都道府県別支援件数の Gini 係数
   性暴力支援センターの利用件数 — 都市部と地方で 100 倍以上の差
   → 「住む場所によって受けられる支援が違う」証明

【キラー指標 3】「沈黙率」
   内閣府調査：DV 被害者の 41.6% が「誰にも相談しなかった」（令和 5 年）
   性暴力被害者の 58.7% が「誰にも相談しなかった」
   → 「半数以上が公式統計に現れない」証明
```

→ **これを LegalShield のプレゼン冒頭に出す** → 補助金審查通過率激増。

---

## Part C — Q3：NPO / 人権弁護士 / 福祉機関 連携 + GPS 就近通報 + 中央監視

### C-1 全体アーキテクチャ

```
┌────────────────────────────────────────────────────────────────┐
│                    LegalShield Dispatch Network                │
│                                                                │
│  受害者                                                         │
│   │ [緊急ボタン / 自動検出]                                     │
│   ▼                                                            │
│  iOS App ── 同意プロファイル ──▶ Tier Decision Engine          │
│                                       │                        │
│              ┌────────────────────────┼─────────────────────┐  │
│              ▼                        ▼                     ▼  │
│         Tier 1                   Tier 2                Tier 3  │
│        生命危険                   緊急                  相談    │
│         │                          │                     │     │
│         ├─ 110 直接               ├─ NPO 緊急ライン     ├─ NPO │
│         ├─ 並行：最寄り NGO       ├─ 弁護士オンコール    ├─ 弁  │
│         └─ 警察と協力             └─ シェルター         └─ 福祉│
│                                                                │
│              ┌────────────────────┴────────────────┐           │
│              ▼                                     ▼           │
│        【Responder Network】                【Central Monitor】│
│        ・弁護士会認証 ID                    ・運営：弁連 + NPO  │
│        ・NPO 法人番号                       │  + 大学 IRB 三方 │
│        ・福祉施設 認可番号                  ・監視内容：        │
│        ・GPS 位置（Opt-in）                 │  ① レスポンス時間│
│        ・対応中フラグ                       │  ② 案件放棄率   │
│        ・対応カテゴリ                       │  ③ システム健康  │
│        ・MOU 締結済み                       │  ④ 個別内容は見ない│
│                                            │  ⑤ 月次公開レポ  │
└────────────────────────────────────────────────────────────────┘
```

### C-2 法的フレームワーク（最重要）

通報・派遣システムを作るとき、踏む法令：

| 法令 | 条文 | 内容 | 対応 |
|------|------|------|------|
| **個情法 27 条** | 第三者提供の制限 | 原則：本人同意必須 | **タイア毎の事前同意（C 同意書 14 項目）** |
| **個情法 27 条 1 項 2 号** | 例外：人の生命保護 | 緊急時は同意なしで提供可 | Tier 1 のみ適用、ログ必須 |
| **DV 防止法 6 条** | 発見者の通報努力義務 | DV 発見時 配偶者暴力相談支援センター・警察に通報努力 | App 機能として組み込み可 |
| **児虐待防止法 6 条** | 通告義務 | 児童虐待を受けたと思われる児童を発見した者は速やかに通告 | 強制的（誰でも） |
| **障害者虐待防止法** | 通報義務 | 同様 | 同様 |
| **ストーカー規制法 4 条** | 警告 | 公安委員会への申出 | App は申出書テンプレ提供のみ |
| **弁護士法 72 条** | 非弁活動 | 報酬目的で法律事務 | **App は紹介のみ、代理は禁止** |
| **社会福祉士法 / 精神保健福祉士法** | 守秘義務 | 福祉従事者の守秘 | Responder 側の MOU で確保 |
| **医師法 / 看護師法** | 守秘義務 | 医療従事者の守秘 | 同上 |
| **電気通信事業法** | 通信の秘密 | 通信内容の取扱 | 登録の検討（規模次第） |

**核心原則：**

```
✅ App は「マッチング・通知」レイヤーのみ
✅ 「相談・支援・代理」は Responder（資格者）が行う
✅ 緊急例外は厳格にログ + 後日本人通知
❌ App が「介入主体」になる設計は避ける
```

### C-3 Tier Decision Engine（具体ロジック）

```python
# legalshield/backend/dispatch/tier_engine.py

class IncidentTier(Enum):
    TIER_1_LIFE = "生命危険・直前"       # 即 110 + 並行通知
    TIER_2_URGENT = "緊急・物理脅威"      # NPO 緊急 + 弁護士オンコール
    TIER_3_CONSULT = "相談・継続支援"     # 通常 NPO・弁護士・福祉

def classify(incident: Incident) -> IncidentTier:
    """
    分類ロジック（人間レビュー前提）
    AI 単独で分類しない（人命に関わるため）
    """
    flags = []
    
    # 自動検出フラグ
    if incident.audio_screaming_detected:        flags.append("scream")
    if incident.heart_rate > 130 and incident.gps_moving_fast:  flags.append("flee")
    if incident.user_pressed_panic_button:       flags.append("panic")
    if incident.weapon_keyword_detected:         flags.append("weapon")
    
    # ルール（保守的に）
    if "panic" in flags or "weapon" in flags or "scream" in flags:
        return IncidentTier.TIER_1_LIFE
    if incident.location_is_unsafe or incident.threat_imminent:
        return IncidentTier.TIER_2_URGENT
    return IncidentTier.TIER_3_CONSULT

def dispatch(incident: Incident, tier: IncidentTier):
    if tier == IncidentTier.TIER_1_LIFE:
        # 個情法 27条1項2号：人の生命保護 → 同意不要
        notify_police(incident)                       # 110
        notify_nearest_npo(incident, radius_km=10, count=3)
        log_emergency_override(incident)              # 監査必須
        notify_user_after_24h("緊急対応のため警察等に通報しました")
    elif tier == IncidentTier.TIER_2_URGENT:
        # 同意済み Responder のみ
        npos = find_responders(incident, radius_km=20, type=["npo_24h", "shelter"], verified=True)
        attorneys = find_responders(incident, radius_km=50, type=["lawyer_on_call"], verified=True)
        notify_priority(npos[:3] + attorneys[:2])
    else:
        # 通常マッチング、ユーザー選択
        candidates = find_responders(incident, radius_km=30, count=10)
        present_to_user(candidates)  # ユーザーが選ぶ
```

### C-4 Responder（応答者）登録・認証

```
登録時に必須：
  ┌────────────────────────────────────┐
  │ Lawyer:                            │
  │   - 弁護士会 ID（弁連 ID）          │
  │   - 所属弁護士会 + 登録番号        │
  │   - 法人形態（個人 / 法律事務所）    │
  │   - MOU 締結（個情法・守秘）        │
  │   - 賠償責任保険 加入確認           │
  ├────────────────────────────────────┤
  │ NPO:                               │
  │   - 法人番号（13桁）                │
  │   - NPO 認証 / 一般社団 / 公益財団  │
  │   - 代表者氏名・連絡先             │
  │   - 24h 対応可否                   │
  │   - 対応エリア（市区町村レベル）     │
  │   - MOU 締結                       │
  ├────────────────────────────────────┤
  │ 福祉施設・支援センター:             │
  │   - 都道府県認可番号                │
  │   - 種別（DV シェルター / 性暴力ワンス│
  │   - 受入容量                       │
  │   - 受入条件                       │
  ├────────────────────────────────────┤
  │ 共通:                              │
  │   - 個資処理委託契約                │
  │   - 緊急時 escalation chart        │
  │   - 月次レポート提出義務            │
  └────────────────────────────────────┘

検証フロー：
  1. オンライン登録（仮）
  2. 書類提出（PDF）
  3. Central Monitor が確認（弁連 / 都道府県問合せ）
  4. MOU 電子署名
  5. アクティブ化
  6. 年次再認証
```

### C-5 GPS 就近通報 — 技術実装

```python
# Backend: PostGIS で半径検索（高速）
import asyncpg

async def find_responders(
    lat: float, 
    lng: float, 
    radius_km: float,
    types: list[str],
    on_call_only: bool = False,
    limit: int = 10,
):
    sql = """
    SELECT 
        id, name, type, phone, on_call,
        ST_Distance(
            location::geography,
            ST_MakePoint($1, $2)::geography
        ) / 1000 AS distance_km
    FROM responders
    WHERE 
        verified = TRUE
        AND active = TRUE
        AND type = ANY($3)
        AND ($4 = FALSE OR on_call = TRUE)
        AND ST_DWithin(
            location::geography,
            ST_MakePoint($1, $2)::geography,
            $5 * 1000  -- meters
        )
    ORDER BY 
        CASE WHEN on_call THEN 0 ELSE 1 END,
        distance_km
    LIMIT $6
    """
    return await pool.fetch(sql, lng, lat, types, on_call_only, radius_km, limit)
```

**位置情報のプライバシー保護：**

```
受害者の GPS：
  - リアルタイム送信は緊急時のみ（Tier 1）
  - 通常時は 市区町村レベル（個人特定不可）
  - on-device で「最寄りエリア」のみ計算
  - サーバーに保存しない（揮発性メモリ → ログのみ）

Responder の GPS：
  - on-call の時のみ（業務時間 opt-in）
  - 半径 100m 程度に obfuscate（プライバシー保護）
  - 受害者には「徒歩 X 分」表示で具体座標見せない
```

### C-6 中央監視（Central Monitor）— 設計と運営

**最重要原則：** 中央監視は「受害者を監視する」ためではなく、「**システムの公正性 + 応答者の質を監視する**」ためのもの。

```
              【Central Monitor 三方共管】
              
              ┌─ 日本弁護士連合会 法人化対応プロジェクト
              ├─ NPO 連合（女性シェルターネット 等 3 団体）
              └─ 大学 IRB（早大 / 一橋 法科大学院）
              
              役割：
              ① 月次レポート公開（透明性）
              ② Responder の不適切対応の調査
              ③ 受害者からの苦情処理
              ④ システム運営者（あなた）の監督
              ⑤ 法令改正への提言

              監視できる：
              ✅ Responder のレスポンス時間（中央値・分布）
              ✅ 案件放棄率（地域別・タイプ別）
              ✅ 受害者からのフィードバックスコア
              ✅ システム障害・通知遅延
              ✅ 個情法インシデント（漏洩等）
              
              監視できない：
              ❌ 個別の受害者の身元
              ❌ 個別の案件内容
              ❌ Responder と受害者の通信内容
              ❌ 受害者の位置情報履歴
```

**技術的に「監視できないこと」を保証：**

```
データレイヤー分離：
  ┌──────────────────┐    ┌──────────────────┐
  │ Operational DB   │    │ Monitor DB        │
  │ （運営者管轄）     │    │ （三方管轄）       │
  ├──────────────────┤    ├──────────────────┤
  │ user_id          │    │ ━━━━ なし ━━━━     │
  │ name             │    │ ━━━━ なし ━━━━     │
  │ phone            │    │ ━━━━ なし ━━━━     │
  │ case_content     │    │ ━━━━ なし ━━━━     │
  │ exact_location   │    │ ━━━━ なし ━━━━     │
  │                  │    │                  │
  │ → 集計 ↓         │    │                  │
  │  metrics_anon    │ ─→ │ metrics_anon     │
  │  - response_time │    │ - response_time  │
  │  - prefecture    │    │ - prefecture    │
  │  - tier          │    │ - tier          │
  │  - outcome       │    │ - outcome       │
  └──────────────────┘    └──────────────────┘
        ↑                       ↑
  運営者のみアクセス        三方理事会のみアクセス
```

### C-7 MOU（Memorandum of Understanding）テンプレ

Responder と LegalShield 運営者の間で結ぶ：

```
覚書（業務提携）

第1条 目的
  本覚書は、運営者が提供する LegalShield Dispatch Network において、
  協力者（Responder）が被害者からの相談に対応するにあたり、両者の
  権利義務を定める。

第2条 協力者の業務
  1. 自身の専門資格・所属法人に基づく被害者支援
  2. 24時間対応の可否を申告
  3. 対応エリア・対応類型を申告

第3条 個人情報の取扱い
  1. 協力者は個情法を遵守する。
  2. 受信した相談情報は、法令に定める保存期間後、削除する。
  3. 第三者への開示は、本人同意 + 法令例外に限る。

第4条 報酬
  1. 本サービスでの被害者紹介について、運営者は協力者から報酬を
     受け取らない（弁護士法72条との整合）。
  2. 協力者と被害者の間の報酬は、両者の直接合意による。

第5条 守秘義務
  1. 双方、相互の経営情報・運営情報を秘匿する。
  2. 違反した場合の損害賠償。

第6条 免責
  1. 運営者は、協力者の対応の結果について責任を負わない。
  2. 協力者は、自身の業務責任で対応する（賠償責任保険必須）。

第7条 監査
  1. 三方共管 Central Monitor の定期監査に協力する。
  2. 不適切対応が判明した場合、是正・登録抹消の対象となる。

第8条 解除
  1. 30日前通知でいつでも解除可能。
  2. 重大違反は即時解除。
```

### C-8 段階的展開計画（Realistic Roadmap）

```
Phase 0（今〜1ヶ月）: 法的基盤
  □ 顧問弁護士契約
  □ 法人化（一般社団法人 推奨）
  □ 個情法対応規程・MOU テンプレ整備
  □ 賠償責任保険 加入

Phase 1（1〜3ヶ月）: パイロット 1 都道府県（東京）
  □ Central Monitor 三方理事会発足
  □ Responder 登録（弁護士 5 名 + NPO 3 団体 + 福祉 2 施設）
  □ Tier Decision Engine v1 実装
  □ Dispatch システム実装
  □ Closed beta 受害者 10〜30 名

Phase 2（3〜6ヶ月）: 5 都道府県拡大
  □ 関東圏 + 関西圏
  □ Responder 50 名以上
  □ 月次レポート公開開始
  □ 補助金申請（Toyota 等）

Phase 3（6〜12ヶ月）: 全国
  □ 47 都道府県カバー
  □ Responder 300 名以上
  □ 国際展開準備（台湾連携）

Phase 4（12ヶ月〜）: 制度化
  □ 法務省・厚労省・内閣府 との対話
  □ 公的補助モデル化
  □ 公益財団法人化を視野
```

### C-9 リスク・落とし穴

| リスク | 対策 |
|--------|------|
| **悪意ある Responder が登録** | 認証厳格化 + 月次質問監査 + 受害者フィードバック |
| **緊急通報の誤検知（過剰）** | Tier 1 は人間レビュー必須 + 30 秒キャンセル猶予 |
| **緊急通報の見逃し（過少）** | デフォルト保守的（false positive 許容） |
| **Responder のオーバーロード** | 件数上限・on-call ローテ |
| **個資漏洩** | Operational/Monitor DB 物理分離 + アクセスログ + 暗号化 |
| **責任のなすりつけ合い** | MOU で明示 + 賠償責任保険 |
| **警察との関係悪化** | 警察庁・各県警と事前協議 + 連携協定 |
| **公的セクターからの圧力** | 三方共管で政治的中立性確保 |
| **媒体報道での被害者特定** | 報道ガイドライン作成 |
| **加害者からの逆襲** | Responder 位置情報 obfuscate + 緊急時運営者通報 |

---

## Part D — 統合実行計画（次の 30 日）

```
Week 1（5/20-5/26）: 基礎
  ✅ Mac→Win 同期確認 [完了]
  ✅ Backend 起動確認 [完了]
  ✅ ユーザー同意書 v1 [完了]
  □ ollama pull gemma3:27b
  □ /rag/diag endpoint
  □ 顧問弁護士見積もり 3 件

Week 2（5/27-6/2）: データ拡張 (Q1+Q2)
  □ judicial_tw.py（最低 1 ヶ月試抓）
  □ jp_underreporting/ 5 個爬蟲（npa_stalking, npa_dv, cao_dv_survey,
     mhlw_jido_soudan, houterasu_stats）
  □ JUDB schema 構築
  □ 「3 つのキラー指標」初版生成

Week 3（6/3-6/9）: Dispatch 設計 (Q3)
  □ 連携制度設計書 v1
  □ 弁連 / NPO 連合 / 大学 IRB 接触
  □ MOU テンプレ法律レビュー
  □ Tier Decision Engine v0 実装

Week 4（6/10-6/16）: 法人化 + 提案
  □ 一般社団法人 設立準備
  □ 補助金申請書（Toyota）に「3 つのキラー指標」追加
  □ Phase 1 パイロット計画書
  □ 弁連法人化対応プロジェクトへ提案
```

---

## 結論：「資料 + 仕組み + 法的保護」の三位一体

```
🇹🇼 台湾資料 (Q1)         🇯🇵 日本資料拡張 (Q2)        🤝 連携 Dispatch (Q3)
  ↓ 分層保管               ↓ 求助無門 DB                ↓ Tier + GPS + 中央監視
  Layer 1: 5-10GB          ① ギャップ係数               Tier 1: 110 並行
  Layer 2: 30-50GB         ② 地域偏在係数               Tier 2: NPO+弁護士
  Layer 3: 100-200GB       ③ 沈黙率                     Tier 3: 通常マッチング
       ↓                        ↓                            ↓
  RAG 強化                  必要性論証                   公的サービス化
       ↓                        ↓                            ↓
  ━━━━━━━━━━━━━ Toyota / 学術 / 公的補助 ━━━━━━━━━━━━━
                          法人化 + 顧問弁護士 + 賠償保険
                            （ユーザー同意書 v1 で守る）
```

---

> ⚠️ **本文件は内部設計案です。**  
> **特に Part C（Dispatch）は実装前に：**  
> **1. 顧問弁護士の全文レビュー**  
> **2. 弁護士会・NPO 連合との事前協議**  
> **3. パイロット規模で実証してから拡大**  
> **を必ず行ってください。**
