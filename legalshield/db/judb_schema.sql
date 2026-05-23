-- ============================================================================
-- JUDB: Japan Underreporting Database
-- ============================================================================
-- 目的: 日本国内の「求助無門」を定量的に裏付ける統合データベース。
--       警察庁・内閣府・厚労省・文科省・法務省・NPO 等の公開統計を集約し、
--       「ギャップ係数」「地域偏在係数」「沈黙率」の3キラー指標を計算。
--
-- DBMS: DuckDB (推奨; 単一ファイル, OLAP最適, FTS拡張) または PostgreSQL
-- 文字コード: UTF-8
-- 作成: 2026-05-20
-- ============================================================================

-- ============================================================================
-- 1. 中核テーブル: 統計観測値 (long format / 1観測値1行)
-- ============================================================================
CREATE TABLE IF NOT EXISTS observations (
    -- 一意識別
    obs_id              VARCHAR PRIMARY KEY,            -- "{source}:{period}:{geo}:{metric}:{hash6}"

    -- 出所
    source              VARCHAR NOT NULL,               -- 'npa' | 'cao' | 'mhlw' | 'mext' | 'moj' | 'houterasu' | 'npo:xxx'
    source_dataset      VARCHAR NOT NULL,               -- 'npa_stalking_annual' 等
    source_url          VARCHAR,
    source_doc_sha256   VARCHAR(64),
    fetched_at          TIMESTAMP NOT NULL,

    -- 期間
    period_type         VARCHAR NOT NULL,               -- 'annual' | 'monthly' | 'quarterly' | 'point'
    period_start        DATE NOT NULL,
    period_end          DATE NOT NULL,
    reiwa_year          INTEGER,                        -- 令和n年 (annual の補助)
    fiscal_year         INTEGER,                        -- 西暦

    -- 地理
    geo_level           VARCHAR NOT NULL,               -- 'national' | 'prefecture' | 'municipality'
    prefecture_code     VARCHAR(2),                     -- JIS X 0401 都道府県コード (01-47)
    prefecture_name     VARCHAR,
    municipality_code   VARCHAR(5),                     -- JIS X 0402 市区町村コード
    municipality_name   VARCHAR,

    -- 事象分類
    crime_category      VARCHAR,                        -- 'stalking' | 'dv' | 'sexual_violence' | 'child_abuse' | 'suicide' | 'ijime' | ...
    victim_attr         VARCHAR,                        -- 'female' | 'male' | 'child' | 'lgbt' | 'elder' | 'all'

    -- 指標
    metric_name         VARCHAR NOT NULL,               -- 'soudan_kensu' | 'kenkyo_kensu' | 'keikoku_kensu' | 'kinshi_meirei' | 'kishou_ritsu' | 'survey_silence_rate' | ...
    metric_value        DOUBLE NOT NULL,
    metric_unit         VARCHAR NOT NULL,               -- 'count' | 'ratio' | 'percent' | 'per_10k' | ...

    -- メタ
    raw_text            VARCHAR,                        -- 抽出元生テキスト断片 (debugging)
    notes               VARCHAR,
    confidence          VARCHAR DEFAULT 'high',         -- 'high' | 'medium' | 'low' (抽出パターンマッチの信頼度)
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_obs_source       ON observations(source, source_dataset);
CREATE INDEX IF NOT EXISTS idx_obs_period       ON observations(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_obs_geo          ON observations(geo_level, prefecture_code);
CREATE INDEX IF NOT EXISTS idx_obs_crime        ON observations(crime_category, victim_attr);
CREATE INDEX IF NOT EXISTS idx_obs_metric       ON observations(metric_name);
CREATE INDEX IF NOT EXISTS idx_obs_year         ON observations(fiscal_year);


-- ============================================================================
-- 2. データソース台帳 (provenance)
-- ============================================================================
CREATE TABLE IF NOT EXISTS sources (
    source_key          VARCHAR PRIMARY KEY,            -- 'npa_stalking_annual'
    publisher           VARCHAR NOT NULL,               -- '警察庁' | '内閣府' | ...
    publisher_division  VARCHAR,                        -- '生活安全局人身安全・少年課' 等
    canonical_url       VARCHAR,
    license             VARCHAR,                        -- '著作権法13条 公的資料' | 'CC-BY' | ...
    update_frequency    VARCHAR,                        -- 'annual' | 'monthly' | ...
    first_year_avail    INTEGER,
    notes               VARCHAR
);


-- ============================================================================
-- 3. 都道府県マスタ (JIS X 0401)
-- ============================================================================
CREATE TABLE IF NOT EXISTS prefectures (
    pref_code           VARCHAR(2) PRIMARY KEY,
    pref_name_ja        VARCHAR NOT NULL,
    pref_name_en        VARCHAR,
    region              VARCHAR,                        -- '北海道' | '東北' | '関東' | ...
    population          INTEGER,                        -- 直近推計 (per_10k 計算用)
    population_year     INTEGER
);


-- ============================================================================
-- 4. 派生ビュー: 「3 つのキラー指標」
-- ============================================================================

-- ----------------------------------------------------------------------------
-- View 1: ギャップ係数 (相談件数 ÷ 検挙件数)
--         「相談しても刑事処分に至らない割合」を地域別・年別に可視化
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_gap_coefficient AS
WITH soudan AS (
    SELECT
        crime_category,
        fiscal_year,
        prefecture_code,
        prefecture_name,
        SUM(metric_value) AS soudan_kensu
    FROM observations
    WHERE metric_name = 'soudan_kensu'
    GROUP BY 1, 2, 3, 4
),
kenkyo AS (
    SELECT
        crime_category,
        fiscal_year,
        prefecture_code,
        prefecture_name,
        SUM(metric_value) AS kenkyo_kensu
    FROM observations
    WHERE metric_name = 'kenkyo_kensu'
    GROUP BY 1, 2, 3, 4
)
SELECT
    s.crime_category,
    s.fiscal_year,
    s.prefecture_code,
    s.prefecture_name,
    s.soudan_kensu,
    k.kenkyo_kensu,
    CASE
        WHEN k.kenkyo_kensu IS NULL OR k.kenkyo_kensu = 0 THEN NULL
        ELSE s.soudan_kensu * 1.0 / k.kenkyo_kensu
    END AS gap_coefficient
FROM soudan s
LEFT JOIN kenkyo k
  ON s.crime_category = k.crime_category
 AND s.fiscal_year = k.fiscal_year
 AND COALESCE(s.prefecture_code, 'NA') = COALESCE(k.prefecture_code, 'NA');


-- ----------------------------------------------------------------------------
-- View 2: 地域偏在係数 (都道府県別利用率の標準偏差・Gini)
--         「住む場所による支援格差」を可視化
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_regional_dispersion AS
WITH per_capita AS (
    SELECT
        o.crime_category,
        o.metric_name,
        o.fiscal_year,
        o.prefecture_code,
        o.prefecture_name,
        o.metric_value,
        p.population,
        CASE
            WHEN p.population IS NULL OR p.population = 0 THEN NULL
            ELSE o.metric_value * 10000.0 / p.population
        END AS per_10k
    FROM observations o
    LEFT JOIN prefectures p ON o.prefecture_code = p.pref_code
    WHERE o.geo_level = 'prefecture'
      AND o.metric_unit = 'count'
)
SELECT
    crime_category,
    metric_name,
    fiscal_year,
    COUNT(*)                     AS pref_n,
    AVG(per_10k)                 AS mean_per_10k,
    STDDEV_SAMP(per_10k)         AS stddev_per_10k,
    MIN(per_10k)                 AS min_per_10k,
    MAX(per_10k)                 AS max_per_10k,
    CASE
        WHEN AVG(per_10k) IS NULL OR AVG(per_10k) = 0 THEN NULL
        ELSE STDDEV_SAMP(per_10k) / AVG(per_10k)
    END                          AS coef_of_variation,    -- CV (≒地域偏在係数)
    CASE
        WHEN MIN(per_10k) IS NULL OR MIN(per_10k) = 0 THEN NULL
        ELSE MAX(per_10k) / MIN(per_10k)
    END                          AS max_min_ratio          -- 最大÷最小
FROM per_capita
WHERE per_10k IS NOT NULL
GROUP BY 1, 2, 3;


-- ----------------------------------------------------------------------------
-- View 3: 沈黙率 (誰にも相談しなかった割合 — アンケート調査由来)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_silence_rate AS
SELECT
    source,
    source_dataset,
    fiscal_year,
    crime_category,
    victim_attr,
    metric_value         AS silence_rate_percent,
    notes,
    source_url
FROM observations
WHERE metric_name = 'survey_silence_rate'
  AND metric_unit = 'percent';


-- ----------------------------------------------------------------------------
-- View 4: 経年トレンド (全国レベル)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_national_trend AS
SELECT
    crime_category,
    metric_name,
    fiscal_year,
    SUM(metric_value)    AS total_value,
    metric_unit
FROM observations
WHERE geo_level = 'national'
GROUP BY 1, 2, 3, 5
ORDER BY 1, 2, 3;


-- ============================================================================
-- 5. 初期データ: 都道府県マスタ (JIS X 0401)
-- ============================================================================
INSERT INTO prefectures (pref_code, pref_name_ja, pref_name_en, region) VALUES
('01', '北海道', 'Hokkaido', '北海道'),
('02', '青森県', 'Aomori', '東北'),
('03', '岩手県', 'Iwate', '東北'),
('04', '宮城県', 'Miyagi', '東北'),
('05', '秋田県', 'Akita', '東北'),
('06', '山形県', 'Yamagata', '東北'),
('07', '福島県', 'Fukushima', '東北'),
('08', '茨城県', 'Ibaraki', '関東'),
('09', '栃木県', 'Tochigi', '関東'),
('10', '群馬県', 'Gunma', '関東'),
('11', '埼玉県', 'Saitama', '関東'),
('12', '千葉県', 'Chiba', '関東'),
('13', '東京都', 'Tokyo', '関東'),
('14', '神奈川県', 'Kanagawa', '関東'),
('15', '新潟県', 'Niigata', '中部'),
('16', '富山県', 'Toyama', '中部'),
('17', '石川県', 'Ishikawa', '中部'),
('18', '福井県', 'Fukui', '中部'),
('19', '山梨県', 'Yamanashi', '中部'),
('20', '長野県', 'Nagano', '中部'),
('21', '岐阜県', 'Gifu', '中部'),
('22', '静岡県', 'Shizuoka', '中部'),
('23', '愛知県', 'Aichi', '中部'),
('24', '三重県', 'Mie', '近畿'),
('25', '滋賀県', 'Shiga', '近畿'),
('26', '京都府', 'Kyoto', '近畿'),
('27', '大阪府', 'Osaka', '近畿'),
('28', '兵庫県', 'Hyogo', '近畿'),
('29', '奈良県', 'Nara', '近畿'),
('30', '和歌山県', 'Wakayama', '近畿'),
('31', '鳥取県', 'Tottori', '中国'),
('32', '島根県', 'Shimane', '中国'),
('33', '岡山県', 'Okayama', '中国'),
('34', '広島県', 'Hiroshima', '中国'),
('35', '山口県', 'Yamaguchi', '中国'),
('36', '徳島県', 'Tokushima', '四国'),
('37', '香川県', 'Kagawa', '四国'),
('38', '愛媛県', 'Ehime', '四国'),
('39', '高知県', 'Kochi', '四国'),
('40', '福岡県', 'Fukuoka', '九州'),
('41', '佐賀県', 'Saga', '九州'),
('42', '長崎県', 'Nagasaki', '九州'),
('43', '熊本県', 'Kumamoto', '九州'),
('44', '大分県', 'Oita', '九州'),
('45', '宮崎県', 'Miyazaki', '九州'),
('46', '鹿児島県', 'Kagoshima', '九州'),
('47', '沖縄県', 'Okinawa', '沖縄')
ON CONFLICT (pref_code) DO NOTHING;


-- ============================================================================
-- 6. 初期データ: ソース台帳
-- ============================================================================
INSERT INTO sources (source_key, publisher, publisher_division, canonical_url, license, update_frequency, first_year_avail, notes) VALUES
('npa_stalking_annual',  '警察庁',   '生活安全局人身安全・少年課',
 'https://www.npa.go.jp/bureau/safetylife/stalker/',
 '著作権法13条', 'annual', 2013,
 'ストーカー事案、配偶者からの暴力事案等についての年次報告'),

('cao_dv_survey',        '内閣府',   '男女共同参画局',
 'https://www.gender.go.jp/policy/no_violence/e-vaw/chousa/index.html',
 '著作権法13条', 'triennial', 1999,
 '男女間における暴力に関する調査 (3年毎)'),

('mhlw_jido_soudan',     '厚生労働省', '子ども家庭局',
 'https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000122802.html',
 '著作権法13条', 'annual', 1990,
 '児童相談所での児童虐待相談対応件数'),

('mhlw_suicide',         '厚生労働省', '社会・援護局',
 'https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/hukushi_kaigo/seikatsuhogo/jisatsu/index.html',
 '著作権法13条', 'annual', 1978,
 '自殺対策白書'),

('mext_ijime',           '文部科学省', '初等中等教育局',
 'https://www.mext.go.jp/a_menu/shotou/seitoshidou/1302902.htm',
 '著作権法13条', 'annual', 1985,
 '児童生徒の問題行動・不登校等生徒指導上の諸課題に関する調査'),

('houterasu_stats',      '法テラス',  '日本司法支援センター',
 'https://www.houterasu.or.jp/',
 '著作権法13条', 'annual', 2006,
 '法テラス利用統計')
ON CONFLICT (source_key) DO NOTHING;
