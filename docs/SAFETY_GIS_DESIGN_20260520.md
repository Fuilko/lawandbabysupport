# Safety GIS — 共管型被害者保護地理情報基盤 設計書

**Doc ID**: `SAFETY_GIS_DESIGN_20260520`
**Status**: Draft v0.1
**Author**: LegalShield Project
**Related**: `EXPANSION_AND_DISPATCH_DESIGN_20260520.md`, `judicial_tw.py`, `judb.py`, `tier_engine.py`

---

## 0. TL;DR

| Want | Can / Can't | How |
|------|------------|-----|
| 写真→「変態」認定DB | ❌ 違法 (個情法 17-2, 27 / 刑法 230) | 諦める |
| 被害者本人が加害者を記録 | ✅ 端末暗号化 only | Sealed Personal Vault |
| 警察+NPO 共管の限定共有DB | ✅ MOU + 同意 + 監査 | Tier B Shared DB |
| 公開情報の集約マップ | ✅ 各県警公開分のみ | Tier A Public Layer |
| 「予測警察」 | ❌ 差別増幅 | やらない |
| **個人**の動線リスク予測 | ✅ 本人合意 + ローカル ML | Personal Risk Routing |
| 既存森林 GIS SaaS の再利用 | ✅ レイヤー/タイル基盤は流用 | 物理 DB 分離 |

---

## 1. アーキテクチャ全体像

```
┌────────────────────────────────────────────────────────────────┐
│  Safety GIS Stack                                              │
│                                                                │
│  ┌─────────────┐  ┌────────────┐  ┌────────────────────────┐  │
│  │ Tier A      │  │ Tier B     │  │ Tier C (Sealed Vault)  │  │
│  │ PUBLIC      │  │ RESTRICTED │  │ PERSONAL (端末暗号化)  │  │
│  │             │  │            │  │                        │  │
│  │ 公開済デ-タ │  │ 警察+NPO   │  │ 被害者本人のみ         │  │
│  │ Aggregator  │  │ 共管DB     │  │ 加害者顔/車番/位置等   │  │
│  └──────┬──────┘  └─────┬──────┘  └───────────┬────────────┘  │
│         │               │                     │               │
│         ▼               ▼                     ▼               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  PostGIS (safety schema, 既存森林DBとは物理分離)        │  │
│  │  ├─ public_incidents  (Tier A)                          │  │
│  │  ├─ shared_alerts     (Tier B, RLS row-level security)  │  │
│  │  ├─ responder_assets  (警察署/交番/NPO/シェルター)      │  │
│  │  ├─ infra_safety      (街灯/防犯カメラ密度)              │  │
│  │  └─ geo_master        (町丁目/メッシュ/47都道府県)       │  │
│  └────────────────────────────────────────────────────────┘  │
│         ▲                                                     │
│         │ (流用)                                              │
│  ┌──────┴─────────────────────────────────────────────────┐  │
│  │  Tile / Layer Engine  ← 既存森林 SaaS と共有可          │  │
│  │  MapLibre + GeoServer / pg_tileserv / Martin            │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Audit & Governance                                     │  │
│  │  ├─ access_log (誰が・いつ・どの行を見たか)             │  │
│  │  ├─ data_subject_request (本人開示・削除請求窓口)       │  │
│  │  └─ steward_board (警察庁/弁連/NPO連/大学IRB の4者)      │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. データ三層モデル

### 2.1 Tier A — Public Layer（公開アグリゲート）

**目的**: 一般市民が地図上で危険傾向と支援拠点を見られる。

**入る**:
- 各都道府県警「不審者情報メール」配信アーカイブ（公開済）
- 警察庁 指名手配（公開分のみ）
- 犯罪統計（町丁目集約以上の粒度、k=20 匿名性確保）
- 警察署・交番・派出所
- NPO 相談センター・女性シェルター（所在公開分のみ／非公開シェルターは絶対に入れない）
- 性犯罪ワンストップ支援センター（厚労省公開）
- 街灯密度・公衆カメラ密度（自治体オープンデータ）

**入らない**:
- 個人の顔写真
- 「この人危険」ラベル
- k<20 の細粒度ピン（特定可能性）
- 非公開シェルター位置（**絶対**）

**ライセンス**: CC-BY または各出典規約準拠

---

### 2.2 Tier B — Restricted Shared Layer（共管限定共有）

**目的**: 警察・NPO・弁護士が**同一案件について**情報共有して被害者を守る。

**アクセス権**: 案件単位の RLS（Row-Level Security）
- 被害者本人が指名した responder のみ閲覧可
- 全閲覧は監査ログに記録（被害者が確認可能）
- 案件終結後 N 日で自動アーカイブ

**入る**:
- 被害者の同意（個情法 17 / 27 同意取得済）の下での加害者情報
- 警察との連携で交付された保護命令・接近禁止命令情報
- NPO 担当者間の引き継ぎメモ
- 緊急時の位置共有（Tier 1 発動時、時間限定）

**法的根拠**:
- 個情法 27-1-1: 法令に基づく場合（DV防止法 8 条 警察援助等）
- 個情法 27-1-2: 人の生命保護必要（Tier 1 のみ）
- 個情法 27 一般: **被害者の事前同意**（Tier 2/3）

**入らない**:
- 同意なしの加害者顔写真の自動共有
- 推測による「危険人物」スコア
- 警察未通報事案の加害者特定情報の NPO 一方的共有

---

### 2.3 Tier C — Sealed Personal Vault（個人封印領域）

**目的**: 被害者本人が自衛のために加害者の特徴を記録する。

**実装**:
- **端末ローカル暗号化 only**（SQLCipher + Secure Enclave / Keystore）
- サーバへの平文同期 **禁止**
- E2E 暗号化バックアップ（鍵は被害者のみ保持）
- 共有時は本人が明示的にエクスポート → 警察 / 弁護士へ証拠提出

**入っていい**:
- 加害者の顔写真（自分が撮ったもの、または相手が SNS 公開しているもの）
- 車両ナンバー
- 接触日時・場所のタイムスタンプ
- 録音・録画（録音は会話当事者なので合法）
- 自分宛のメッセージスクショ

**禁止**:
- 第三者の顔写真の同時記録（無関係者の個人情報）
- 加害者の住所詮索結果（個情法・ストーカー規制法逆抵触）

**顔認識の使い方（合法）**:
- ✅ Tier C 内で「同じ人物が複数回出現」を本人にだけ知らせる（自衛）
- ✅ 警察への提出時、本人の意思で
- ❌ Tier A/B サーバへ送る
- ❌ 他ユーザーと照合

---

## 3. PostGIS スキーマ（safety schema, 既存森林 DB と物理分離）

```sql
CREATE SCHEMA safety;

-- ----------------------------------------------------------------
-- Tier A: PUBLIC
-- ----------------------------------------------------------------
CREATE TABLE safety.public_incidents (
    id                  BIGSERIAL PRIMARY KEY,
    source              TEXT NOT NULL,            -- 'mpd_fushinsha' | 'npa_wanted' | ...
    source_doc_url      TEXT,
    incident_type       TEXT NOT NULL,            -- 'stalking' | 'sexual_harassment' | 'theft' | ...
    occurred_at         TIMESTAMPTZ NOT NULL,
    reported_at         TIMESTAMPTZ,
    -- 粒度制御: 個人特定回避のため町丁目重心または 250m メッシュ重心のみ
    geom_centroid       GEOMETRY(Point, 4326) NOT NULL,
    geom_resolution_m   INTEGER NOT NULL CHECK (geom_resolution_m >= 100),
    prefecture_code     VARCHAR(2),
    municipality_code   VARCHAR(5),
    mesh_code_1km       VARCHAR(8),
    description         TEXT,                     -- 公開済の文言のみ
    license             TEXT,
    ingested_at         TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON safety.public_incidents USING GIST(geom_centroid);
CREATE INDEX ON safety.public_incidents (occurred_at);
CREATE INDEX ON safety.public_incidents (incident_type);

-- Aggregated heatmap view (k>=20 のみ)
CREATE MATERIALIZED VIEW safety.public_incidents_heatmap_500m AS
SELECT
    ST_SnapToGrid(geom_centroid::geometry, 0.005) AS cell,
    incident_type,
    date_trunc('month', occurred_at) AS month,
    count(*) AS n
FROM safety.public_incidents
GROUP BY 1, 2, 3
HAVING count(*) >= 20;
CREATE INDEX ON safety.public_incidents_heatmap_500m USING GIST(cell);

-- ----------------------------------------------------------------
-- Tier A: Responder assets (公開可)
-- ----------------------------------------------------------------
CREATE TABLE safety.responder_assets (
    id              BIGSERIAL PRIMARY KEY,
    asset_type      TEXT NOT NULL,                -- 'police' | 'koban' | 'npo' | 'shelter_public' | 'onestop_sexcrime' | 'hospital_er'
    name            TEXT NOT NULL,
    geom            GEOMETRY(Point, 4326) NOT NULL,
    phone           TEXT,
    hours           TEXT,
    is_public       BOOLEAN NOT NULL DEFAULT true,
    notes           TEXT,
    updated_at      TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT no_secret_shelter
      CHECK (asset_type <> 'shelter_secret')      -- 非公開シェルターは別 DB 必須
);
CREATE INDEX ON safety.responder_assets USING GIST(geom);
CREATE INDEX ON safety.responder_assets (asset_type);

-- ----------------------------------------------------------------
-- Tier A: Infrastructure for safety
-- ----------------------------------------------------------------
CREATE TABLE safety.infra_safety (
    id              BIGSERIAL PRIMARY KEY,
    kind            TEXT NOT NULL,                -- 'streetlight' | 'cctv_public' | 'emergency_pole'
    geom            GEOMETRY(Point, 4326) NOT NULL,
    intensity       REAL,
    source          TEXT,
    updated_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON safety.infra_safety USING GIST(geom);

-- ----------------------------------------------------------------
-- Tier B: RESTRICTED (Row-Level Security 必須)
-- ----------------------------------------------------------------
CREATE TABLE safety.cases (
    case_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    victim_user_id  UUID NOT NULL,                -- pseudonym, 直接識別不可
    opened_at       TIMESTAMPTZ DEFAULT now(),
    closed_at       TIMESTAMPTZ,
    crime_category  TEXT,
    consent_ref     UUID NOT NULL,                -- 同意取得記録への FK
    steward_org     TEXT                          -- 案件主管 (NPO名)
);

CREATE TABLE safety.case_members (
    case_id         UUID REFERENCES safety.cases(case_id) ON DELETE CASCADE,
    responder_id    UUID NOT NULL,
    role            TEXT NOT NULL,                -- 'police' | 'npo_lead' | 'attorney' | 'social_worker'
    granted_at      TIMESTAMPTZ DEFAULT now(),
    revoked_at      TIMESTAMPTZ,
    PRIMARY KEY (case_id, responder_id)
);

CREATE TABLE safety.shared_alerts (
    alert_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id         UUID NOT NULL REFERENCES safety.cases(case_id),
    alert_type      TEXT NOT NULL,                -- 'protection_order' | 'sighting' | 'escalation'
    geom            GEOMETRY(Point, 4326),        -- 任意
    geom_blur_m     INTEGER DEFAULT 100,
    occurred_at     TIMESTAMPTZ NOT NULL,
    posted_by       UUID NOT NULL,
    body_encrypted  BYTEA NOT NULL,               -- 案件鍵で暗号化
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON safety.shared_alerts USING GIST(geom);
CREATE INDEX ON safety.shared_alerts (case_id);

-- RLS: case_members に登録された responder のみ閲覧可
ALTER TABLE safety.shared_alerts ENABLE ROW LEVEL SECURITY;
CREATE POLICY shared_alerts_member_only ON safety.shared_alerts
    FOR SELECT
    USING (
        case_id IN (
            SELECT case_id FROM safety.case_members
            WHERE responder_id = current_setting('app.current_responder_id')::uuid
              AND revoked_at IS NULL
        )
    );

-- ----------------------------------------------------------------
-- Audit
-- ----------------------------------------------------------------
CREATE TABLE safety.access_log (
    log_id          BIGSERIAL PRIMARY KEY,
    at              TIMESTAMPTZ DEFAULT now(),
    actor_id        UUID,
    actor_role      TEXT,
    action          TEXT,                         -- 'SELECT' | 'INSERT' | 'EXPORT' | 'DECRYPT'
    table_name      TEXT,
    row_pk          TEXT,
    case_id         UUID,
    ip_hash         TEXT,
    purpose         TEXT
);
CREATE INDEX ON safety.access_log (at);
CREATE INDEX ON safety.access_log (case_id);

CREATE TABLE safety.data_subject_request (
    req_id          BIGSERIAL PRIMARY KEY,
    received_at     TIMESTAMPTZ DEFAULT now(),
    request_type    TEXT NOT NULL,                -- 'disclosure' | 'correction' | 'deletion' | 'opt_out'
    subject_email   TEXT,
    subject_proof   TEXT,                         -- 本人確認方法の記録
    handled_by      TEXT,
    handled_at      TIMESTAMPTZ,
    outcome         TEXT,
    notes           TEXT
);
```

**重要**: `safety` スキーマは森林 DB と**別 PostgreSQL ロール / 別バックアップ / 別暗号鍵**で運用すること。

---

## 4. 既存森林 GIS SaaS の活かし方

| レイヤ | 流用 | 別途 |
|--------|------|------|
| MapLibre / Leaflet フロント | ✅ 流用 | スタイルだけ別 |
| ベクター/ラスタータイル配信 | ✅ 流用 | 別エンドポイント |
| PostGIS インスタンス | ⚠️ **物理分離推奨** | safety DB を別 RDS / 別 VPS |
| 認証基盤 | ⚠️ Tier A は OK、Tier B は責任分離が必要 | Tier B 用は別 IDP (e.g. Keycloak + 多要素必須) |
| 監視 (Prometheus/Grafana) | ✅ 流用 | safety メトリクスは別ダッシュボード |
| バックアップ | ❌ 必ず分離 | 鍵管理は steward_board が共同保管 |

**推奨スタック**:
```
PostGIS 16 + pg_partman (時系列パーティション)
   ↓
pg_tileserv (MVT 配信) + pg_featureserv (OGC API)
   ↓
MapLibre GL JS + deck.gl (ヒートマップ/3D)
   ↓
FastAPI (Tier B 限定共有 API、JWT + RLS injection)
```

---

## 5. 顔認識の合法な実装パス

```
[被害者の iPhone]
   │
   ├─ カメラで加害者撮影 (自衛/証拠保全目的)
   │
   ├─ Tier C Vault (端末ローカル, SQLCipher)
   │   └─ Vision Framework + Core ML で顔エンベディング生成
   │       → 同一人物が再出現したら本人に通知
   │
   ├─ [本人が明示エクスポート]
   │   ↓
   │   警察提出 (E2E 暗号化 zip + パスワード別送)
   │
   └─ [絶対しない]
       ↓
       サーバへ送信 → 他ユーザーと照合 → 「変態DB」化
```

**ライブラリ選定**:
- iOS: Vision Framework (`VNGenerateFaceDescriptor`) + Core ML
- Android: ML Kit Face Detection + custom embedding (MediaPipe Face Mesh)
- 顔エンベディングは **端末から出さない**
- 写真本体も Secure Enclave で鍵管理

**法的位置づけ**:
- 「自分の身を守るために必要な範囲での記録」= 私的領域 (個情法 5 条「個人情報取扱事業者」に該当しない私的利用)
- ただし、エクスポート後の取扱は責任が移る → 警察以外への共有は禁止のガイダンスを UI に明示

---

## 6. Risk / Trend / Prediction の正しいやり方

| 旧来「予測警察」 | Safety GIS の方針 |
|------------------|--------------------|
| 「この地域の犯罪率が高い」スコア表示 | **やらない** (差別増幅) |
| 過去事件多発地に警官配備提案 | **AI は提案しない** (人間判断のみ) |
| 個人の「危険人物」スコア | **やらない** |
| 「あなたの 1km 圏内に性犯罪発生」プッシュ | **やらない** (パニック誘発) |
| **個人の動線**に対する安全ルート提示 | ✅ やる |
| **時間帯別**の街灯密度マッチ | ✅ やる |
| **本人通報後**の予測：再被害リスク (個人内モデル) | ✅ やる |
| 集約統計の経年トレンド (地域名なし) | ✅ やる |

### 6.1 Personal Risk Routing（合法な「予測」）

入力（端末ローカルのみ）:
- 過去の不快遭遇地点（本人記録）
- 現在地・目的地・時刻
- 加害者の出没傾向（本人 Vault データ）

サーバ呼出:
- 公開不審者情報ヒートマップ（k>=20 集約のみ）
- 街灯密度
- 公共施設・交番位置

出力:
- 推奨ルート（距離より安全度重み）
- 「この道は街灯が少ないので別ルート推奨」
- **「ここで犯罪が起きやすい」とは言わない**

---

## 7. Co-Governance（共管統治）

### 7.1 Steward Board（4 者制衡）

| 構成 | 権限 | 責任 |
|------|------|------|
| 警察庁 / 各県警 代表 | Tier A データの正当性監査、Tier B 緊急時アクセス承認 | 警察データの提供 |
| 弁護士連合会 | 個情法/弁護士法/憲法適合性監査 | 法的助言・利用者代理 |
| NPO 連合（女性シェルター・ぱっぷす・Lifelink 等） | 被害者視点の運用基準、Tier B 主幹 | 現場対応 |
| 大学 IRB（社会学・情報倫理） | 統計利用/研究利用の倫理審査、年次外部監査 | 透明性レポート公開 |

**4 者の過半数**でないと:
- スキーマ変更不可
- 新規データソース追加不可
- 第三者提供不可

### 7.2 透明性

四半期ごとに公開:
- Tier A レコード数・出典別内訳
- Tier B 案件数（個別案件は秘匿）
- アクセスログ集計（誰が何件閲覧したか、役割別）
- 本人開示請求対応件数 / 平均日数
- 監査指摘事項と対応

### 7.3 被害者の権利

- 自分の案件のアクセスログを **いつでも見られる**
- 「この responder の閲覧を取り消す」即時実行可
- 案件削除請求は 7 日以内に実行
- 異議申立窓口: 弁連 / IRB（中立）

---

## 8. 補助金/制度化での売り方

| 受け手 | 殺し文句 |
|--------|---------|
| 警察庁 | 「不審者情報の利活用率を 100 倍に。市民の自衛が **公的データから始まる** 初の基盤」 |
| 内閣府男女共同参画 | 「DV/性犯罪相談ギャップ係数 18 倍を可視化し、現場 NPO と 24h 接続」 |
| 自治体 | 「街灯整備の優先順位を **被害者動線データ** で根拠化」 |
| 豊田財団等 | 「**予測警察を導入しない宣言**を出した世界初の被害者中心 GIS」 |
| 学会 (情報法/犯罪学) | 「Steward Board モデルで運営透明性を担保」 |

---

## 9. Phase 計画

### Phase 0 (今 - 2 週間)
- [ ] safety schema を森林 DB から物理分離した PostGIS インスタンスに作成
- [ ] Tier A 用に **MPD 不審者情報** を 1 ヶ月試スクレイプ → 250m メッシュ集約 → 地図表示
- [ ] responder_assets に警察署/交番（国土数値情報 P28）と相談センター（厚労省公開）を入れる

### Phase 1 (1 ヶ月)
- [ ] MapLibre フロントで Tier A だけ可視化（公開デモ）
- [ ] 弁連 / NPO 連合に Steward Board 打診（既存 Dispatch 設計と一体提案）
- [ ] iOS Tier C Vault プロトタイプ（SQLCipher + Vision Framework）

### Phase 2 (2-3 ヶ月)
- [ ] Tier B RLS 実装 + 1 NPO とパイロット
- [ ] Personal Risk Routing v0（街灯密度のみ）
- [ ] 補助金申請（豊田/内閣府/JST RISTEX）

### Phase 3 (6 ヶ月+)
- [ ] Steward Board 正式発足
- [ ] 全国 NPO へ拡大
- [ ] 透明性レポート Q1 公開

---

## 10. 絶対やらないことリスト（憲章）

1. 私的「変態 DB」「危険人物 DB」を運営しない
2. 顔エンベディングをサーバへ送信しない
3. 同意なしの第三者顔写真を取得・保存しない
4. 地域に対する「犯罪率」スコアを表示しない
5. 非公開シェルター位置を DB に入れない
6. k<20 の細粒度地理情報を一般公開しない
7. 警察以外への加害者情報の一方的共有をしない
8. 予測警察 / 個人危険スコアを実装しない
9. データ削除要求を 7 日以上保留しない
10. Steward Board 過半数なしにスキーマ変更しない

---

## Appendix A. 関連法令

| 法令 | 該当条文 | 影響 |
|------|---------|------|
| 個人情報保護法 | 2-2, 17-2, 27, 28 | 顔写真=個人識別符号、犯罪歴=要配慮、同意取得義務 |
| 刑法 | 230 (名誉毀損), 231 (侮辱) | 「変態」ラベル付け即抵触 |
| 民法 | 709, 710 | プライバシー侵害損害賠償 |
| ストーカー規制法 | 2 条, 18 条 | 加害者所在追跡が**逆に**該当する危険 |
| 軽犯罪法 | 1-23 (のぞき) | 撮影方法によっては抵触 |
| DV 防止法 | 8, 8 の 2 | 警察援助・接近禁止命令 |
| 児童虐待防止法 | 6 (通告義務) | 児童が関与する場合 |
| 弁護士法 | 72 | 法律事務代行禁止 (App は仲介のみ) |
| 著作権法 | 13 | 公的統計は公共領域 |

---

**End of Document**
