-- LegalShield-jp: Intake & Routing schema (智能法律分流官)
-- Adds: problem_category / category_routing / org_specialty / case_outcome / intake_session
-- Idempotent — safe to re-run.

-- ─────────────────────────────────────────────────────────────
-- problem_category : 困りごとのカノニカル分類
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS legalshield.problem_category (
  code            TEXT PRIMARY KEY,                            -- 'dv', 'stalking', 'product_defect' ...
  name_ja         TEXT NOT NULL,
  name_en         TEXT,
  description_ja  TEXT,
  severity_default TEXT NOT NULL CHECK (severity_default IN ('critical','high','medium','low')),
  urgent_hotline  TEXT,                                        -- '#8008' / '110' / '189' ...
  parent_code     TEXT REFERENCES legalshield.problem_category(code),
  tags            TEXT[] DEFAULT '{}',                         -- ['gender','child','workplace',...]
  display_order   INT DEFAULT 999,
  is_active       BOOLEAN DEFAULT TRUE,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_problem_category_severity
  ON legalshield.problem_category (severity_default);
CREATE INDEX IF NOT EXISTS idx_problem_category_tags
  ON legalshield.problem_category USING GIN (tags);

-- ─────────────────────────────────────────────────────────────
-- category_routing : ドメイン専門家がキュレートする tier ベース推奨
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS legalshield.category_routing (
  id                  BIGSERIAL PRIMARY KEY,
  category_code       TEXT NOT NULL REFERENCES legalshield.problem_category(code) ON DELETE CASCADE,
  tier                INT NOT NULL CHECK (tier BETWEEN 1 AND 5),
  org_kind            TEXT NOT NULL,                           -- 'hotline'|'admin_center'|'npo'|'bar_assoc'|'court'|'police'|'shelter'
  org_name_pattern    TEXT,                                    -- '配偶者暴力相談支援センター' etc. (used to match support_org.name)
  weight              NUMERIC(3,2) NOT NULL DEFAULT 1.0,       -- ベース重み（同じtier内での順位）
  trigger_condition   TEXT NOT NULL DEFAULT 'always',          -- 'always'|'if_immediate_danger'|'if_evidence_strong'|'if_money_lost_high' ...
  what_to_say_ja      TEXT,                                    -- 「行ったら最初に言うこと」スクリプト
  documents_needed_ja TEXT[] DEFAULT '{}',                     -- 持参書類チェックリスト
  expected_outcome_ja TEXT,                                    -- 期待される対応
  next_tier_if_ja     TEXT,                                    -- エスカレーション条件
  notes_ja            TEXT,
  source              TEXT DEFAULT 'curated_v1',               -- knowledge provenance
  UNIQUE (category_code, tier, org_kind)
);
CREATE INDEX IF NOT EXISTS idx_category_routing_cat
  ON legalshield.category_routing (category_code, tier);

-- ─────────────────────────────────────────────────────────────
-- org_specialty : 各組織の category 別の特化度・有効性スコア
--   specialty_score      : ドメイン知識による特化度 (0..1)
--   effectiveness_score  : 観測ベースの解決率 (0..1, ベイズ更新)
--   case_count           : 観測ケース数（信頼区間計算用）
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS legalshield.org_specialty (
  org_id              BIGINT NOT NULL REFERENCES legalshield.support_org(id) ON DELETE CASCADE,
  category_code       TEXT NOT NULL REFERENCES legalshield.problem_category(code) ON DELETE CASCADE,
  specialty_score     NUMERIC(4,3) NOT NULL DEFAULT 0.500 CHECK (specialty_score BETWEEN 0 AND 1),
  effectiveness_score NUMERIC(4,3) NOT NULL DEFAULT 0.500 CHECK (effectiveness_score BETWEEN 0 AND 1),
  case_count          INT NOT NULL DEFAULT 0,
  language_support    TEXT[] DEFAULT '{ja}',                   -- ['ja','en','zh','ko','vi',...]
  cost_tier           TEXT DEFAULT 'unknown' CHECK (cost_tier IN ('free','low','sliding','paid','unknown')),
  confidential        BOOLEAN DEFAULT TRUE,
  hours_24_7          BOOLEAN DEFAULT FALSE,
  notes_ja            TEXT,
  last_assessed       TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (org_id, category_code)
);
CREATE INDEX IF NOT EXISTS idx_org_specialty_cat
  ON legalshield.org_specialty (category_code, effectiveness_score DESC);

-- ─────────────────────────────────────────────────────────────
-- case_outcome : 匿名化された実ケースの転帰（モデル更新の唯一真実源）
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS legalshield.case_outcome (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  intake_session_id   UUID,                                    -- FK to intake_session if exists
  category_code       TEXT REFERENCES legalshield.problem_category(code),
  prefecture_code     CHAR(2),
  org_id              BIGINT REFERENCES legalshield.support_org(id),
  outcome             TEXT NOT NULL CHECK (outcome IN ('resolved','partial','unresolved','redirected','withdrawn','in_progress')),
  duration_days       INT,
  user_feedback_score INT CHECK (user_feedback_score BETWEEN 1 AND 5),
  free_notes          TEXT,                                    -- already redacted/anonymized client-side
  recorded_at         TIMESTAMPTZ DEFAULT NOW(),
  is_synthetic        BOOLEAN DEFAULT FALSE                    -- TRUE if domain-expert seeded for bootstrap
);
CREATE INDEX IF NOT EXISTS idx_case_outcome_cat
  ON legalshield.case_outcome (category_code, outcome);
CREATE INDEX IF NOT EXISTS idx_case_outcome_org
  ON legalshield.case_outcome (org_id);

-- ─────────────────────────────────────────────────────────────
-- intake_session : 利用者の問診セッション（オンデバイス先行 → 任意 cloud sync）
--   raw_text は原則オンデバイスのみ。サーバ保存は明示的同意ベース。
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS legalshield.intake_session (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_hash         TEXT,                                    -- sha256 of (device_uuid + salt), never raw IP/UA
  detected_category   TEXT REFERENCES legalshield.problem_category(code),
  detected_severity   TEXT CHECK (detected_severity IN ('critical','high','medium','low')),
  detected_tags       TEXT[] DEFAULT '{}',
  language            TEXT DEFAULT 'ja',
  prefecture_code     CHAR(2),
  geom                GEOGRAPHY(POINT, 4326),                  -- approximate (city level), never exact
  raw_text_consent    BOOLEAN DEFAULT FALSE,                   -- did user consent to upload raw text?
  raw_text_redacted   TEXT,                                    -- only stored if consent=TRUE, after PII redaction
  llm_model           TEXT,                                    -- 'ondevice-llama3-8b-q4' / 'cloud-gpt-4o-mini' ...
  llm_confidence      NUMERIC(4,3),                            -- 0..1
  recommended_org_ids BIGINT[] DEFAULT '{}',                   -- ranked output snapshot
  recommendation_json JSONB,                                   -- full ranked result with reasoning
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  followed_up         BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_intake_session_created
  ON legalshield.intake_session (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_intake_session_category
  ON legalshield.intake_session (detected_category);

-- ─────────────────────────────────────────────────────────────
-- VIEW: ランキング用結合ビュー（API がそのまま使える）
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW legalshield.v_org_for_category AS
SELECT
  s.id              AS org_id,
  s.name,
  s.org_type,
  s.prefecture_code,
  s.geom,
  s.contact,
  os.category_code,
  os.specialty_score,
  os.effectiveness_score,
  os.case_count,
  os.language_support,
  os.cost_tier,
  os.confidential,
  os.hours_24_7,
  pc.severity_default,
  pc.urgent_hotline
FROM legalshield.support_org s
JOIN legalshield.org_specialty os ON os.org_id = s.id
JOIN legalshield.problem_category pc ON pc.code = os.category_code;

-- ─────────────────────────────────────────────────────────────
-- 初期 SEED: 12 problem_category
-- ─────────────────────────────────────────────────────────────
INSERT INTO legalshield.problem_category (code, name_ja, name_en, description_ja, severity_default, urgent_hotline, tags, display_order) VALUES
  ('dv',                  '配偶者・パートナー暴力（DV）',     'Domestic Violence',           '身体的・精神的・経済的・性的暴力を含む配偶者間／親密関係内の暴力',                          'critical', '#8008',           ARRAY['gender','partner','urgent'],         10),
  ('stalking',            'ストーカー被害',                    'Stalking',                    'つきまとい、待ち伏せ、無言電話、SNS監視等',                                                'critical', '110',             ARRAY['gender','partner','urgent'],         20),
  ('sexual_violence',     '性犯罪・性暴力',                    'Sexual Violence',             '強制性交等罪、強制わいせつ、痴漢、盗撮、リベンジポルノ等',                                  'critical', '#8891',           ARRAY['gender','urgent'],                   30),
  ('child_abuse',         '児童虐待',                          'Child Abuse',                 '身体的・性的・心理的虐待、ネグレクト',                                                       'critical', '189',             ARRAY['child','urgent'],                    40),
  ('elder_abuse',         '高齢者虐待',                        'Elder Abuse',                 '介護施設・家庭内の身体的虐待、ネグレクト、経済的搾取',                                       'high',     '地域包括支援センター', ARRAY['elder'],                          50),
  ('school_bullying',     'いじめ・スクールハラスメント',     'School Bullying',             '学校内いじめ、教師による不適切指導、不登校関連',                                            'high',     '0120-0-78310',    ARRAY['child','education'],                 60),
  ('workplace_harassment','職場ハラスメント',                  'Workplace Harassment',        'パワハラ・セクハラ・マタハラ・ケアハラ等',                                                   'high',     '0570-919-471',    ARRAY['workplace','labor'],                 70),
  ('labor_violation',     '労働基準法違反・賃金未払い',       'Labor Violation',             '残業代未払い、解雇トラブル、過労死、労災隠蔽',                                              'high',     '0120-811-610',    ARRAY['workplace','labor'],                 80),
  ('foreign_worker',      '外国人労働者の権利侵害',           'Foreign Worker Rights',       '技能実習生問題、不当解雇、パスポート取り上げ、言語的支援不足',                              'high',     '0570-011000',     ARRAY['workplace','foreign','language'],    90),
  ('consumer_fraud',      '消費者被害・契約トラブル',         'Consumer Fraud',              '訪問販売・電話勧誘・SF商法・架空請求・サブスク詐欺',                                         'medium',   '188',             ARRAY['consumer'],                         100),
  ('product_defect',      '製品欠陥・PL被害',                  'Product Liability',           'ドローン墜落、自動車欠陥、家電事故、医療機器不具合等',                                       'high',     '188',             ARRAY['consumer','tech'],                  110),
  ('admin_grievance',     '行政手続きの不利益・通報後の家族分離等', 'Administrative Grievance', '行政の機械的対応、児童相談所の過剰介入、生活保護打切り等',                                   'high',     '0570-003-110',    ARRAY['admin','family'],                   120)
ON CONFLICT (code) DO UPDATE SET
  name_ja=EXCLUDED.name_ja, description_ja=EXCLUDED.description_ja,
  severity_default=EXCLUDED.severity_default, urgent_hotline=EXCLUDED.urgent_hotline,
  tags=EXCLUDED.tags, display_order=EXCLUDED.display_order;

-- ─────────────────────────────────────────────────────────────
-- 初期 SEED: category_routing（DV / stalking / product_defect / foreign_worker / admin_grievance）
-- 残りカテゴリは後続の seed file で追加
-- ─────────────────────────────────────────────────────────────
INSERT INTO legalshield.category_routing
  (category_code, tier, org_kind, org_name_pattern, weight, trigger_condition,
   what_to_say_ja, documents_needed_ja, expected_outcome_ja, next_tier_if_ja, notes_ja, source) VALUES

-- DV ─────────────────────────────
('dv', 1, 'hotline', 'DV相談ナビ #8008', 1.00, 'always',
 '「今、安全な場所にいません」または「DVを受けています」と最初に伝える。氏名は名乗らなくて良い。',
 ARRAY['不要（電話のみ）'],
 '24時間体制で最寄りの配偶者暴力相談支援センターまたは女性相談支援センターに自動接続される。',
 '即座の保護が必要な場合 → tier 2 警察 110番／配暴センター直行',
 '内閣府男女共同参画局所管。全国共通短縮ダイヤル。', 'curated_v1'),

('dv', 2, 'admin_center', '配偶者暴力相談支援センター', 0.95, 'always',
 '「DVを受けており、相談・保護の申し出をしたい」と伝える。子供同伴の場合はその旨も。',
 ARRAY['身分証明書（あれば）','保険証（あれば）','診断書・ケガの写真（あれば）','子供の母子手帳（同行時）'],
 '一時保護所の手配（即日可能）／医療機関連携／生活保護申請支援／加害者からの隔離手続き案内。',
 '保護命令が必要 → tier 4 弁護士会／法テラス',
 '都道府県・政令市単位で設置。子供は18歳未満でも同伴可（DV防止法6条の2）。', 'curated_v1'),

('dv', 2, 'police', '警察 110 / 各署の生活安全課', 0.90, 'if_immediate_danger',
 '「DV被害を受けており、身の危険があります」と伝える。具体的な脅迫・暴力の有無を端的に。',
 ARRAY['ケガの写真・診断書','加害者の連絡先・氏名','過去の被害記録（時系列メモ）'],
 '緊急避難の支援、加害者への警告、被害届受理（必要時）、ストーカー規制法・DV防止法の保護命令申請の案内。',
 '民事的解決を求める場合 → tier 4 弁護士会',
 '注意: 通報後の家族分離リスクが心配な場合は、まず tier 2 配暴センターに相談を推奨（個別支援可）。', 'curated_v1'),

('dv', 3, 'npo', '民間 DV シェルター・支援団体（全国女性シェルターネット 等）', 0.85, 'always',
 '「公的窓口に行きづらい事情があります」「匿名で相談したい」「外国籍／LGBTQ／高齢で一般窓口で対応されない」等、特殊事情を率直に。',
 ARRAY['ない場合は手ぶらで OK'],
 '一時保護（公的シェルターより柔軟）／同行支援／生活再建支援／法的支援への接続。',
 '法的手続きへの移行 → tier 4 弁護士会／法テラス',
 '外国籍・LGBTQ・障害・高齢者等の特殊事情に強い団体が多い。費用は原則無料または応相談。', 'curated_v1'),

('dv', 4, 'bar_assoc', '弁護士会 法律相談センター（DV専門）', 0.80, 'always',
 '「DV被害があり、保護命令申立／離婚／親権／慰謝料を含む法的手続きを検討したい」と伝える。',
 ARRAY['婚姻関係の証明（戸籍謄本）','DV の証拠（写真、録音、医療記録、SNS スクショ）','加害者の財産情報（あれば）'],
 '保護命令申立の支援（地裁直送）／離婚調停申立／慰謝料・財産分与の方針提示。',
 '弁護士費用が払えない → 同 tier の法テラスに切替',
 '初回 30 分無料相談あり。日弁連 DV 法律相談ホットライン（全国共通）。', 'curated_v1'),

('dv', 4, 'admin_center', '法テラス（民事法律扶助）', 0.78, 'if_low_income',
 '「DV被害で離婚／保護命令を希望、収入要件に該当します」と伝える。',
 ARRAY['収入証明（源泉徴収票・住民税課税証明等）','身分証','離婚意思の整理メモ'],
 '弁護士費用の立替（償還型）／DV特例で配偶者の収入は計算除外。',
 '裁判所申立段階に進むなら同弁護士が継続担当',
 '民事法律扶助制度。立替金は原則月 5,000 円〜の分割返済。', 'curated_v1'),

('dv', 5, 'court', '家庭裁判所（保護命令／離婚調停）', 0.70, 'if_evidence_strong',
 '弁護士同伴。本人尋問・書面提出。',
 ARRAY['弁護士に依頼済の場合は弁護士が準備'],
 '保護命令（接近禁止・退去命令）／離婚成立／親権・養育費決定。',
 '相手方が判決不服 → 控訴審／上告審',
 '保護命令は緊急の場合 1 週間以内で発令可能。', 'curated_v1'),

-- stalking ─────────────────────────────
('stalking', 1, 'police', '警察 110 / 各署の生活安全課', 1.00, 'always',
 '「ストーカー被害を受けており、警告・禁止命令を希望します」',
 ARRAY['加害者の特定情報','つきまとい等の記録（時系列、写真、SNS スクショ）','音声・動画証拠'],
 'ストーカー規制法に基づく警告／禁止命令の検討（行政処分）／緊急時の保護。',
 '民事的接近禁止仮処分が必要 → tier 4 弁護士会',
 'ストーカー規制法は民事ではなく行政処分。警察主導。', 'curated_v1'),

('stalking', 2, 'admin_center', '配偶者暴力相談支援センター（元配偶者ストーキングの場合）', 0.85, 'if_partner_origin',
 '「元パートナーからのストーカー被害を受けています」',
 ARRAY['DV と同じ'],
 '保護的支援（DV と同等のスキーム適用可）。',
 '法的処分が必要 → tier 1 警察',
 'ストーカー被害が元配偶者・元交際相手由来の場合、DV 防止法の保護命令も併用可能。', 'curated_v1'),

('stalking', 3, 'npo', '全国ストーカー被害者支援団体・SNS 専門 NPO', 0.75, 'always',
 '「警察に行く前に整理したい」「証拠保全を学びたい」と伝える。',
 ARRAY['不要'],
 '証拠保全のアドバイス、警察同行支援、SNS プラットフォームへの削除申請支援。',
 '法的手続き → tier 4',
 'SNS ストーキングは技術的支援が肝心。', 'curated_v1'),

('stalking', 4, 'bar_assoc', '弁護士会（ストーカー・SNS 削除請求対応）', 0.70, 'always',
 '「ストーカー被害があり、接近禁止仮処分／発信者情報開示請求を行いたい」',
 ARRAY['証拠一式（時系列、SNS、通信記録）','弁護士費用の準備'],
 '仮処分申立／プロバイダ責任制限法に基づく発信者情報開示／民事損害賠償。',
 '判決へ',
 '東京・大阪・福岡等大都市にネット問題専門弁護士が多数。', 'curated_v1'),

-- product_defect ─────────────────────────────
('product_defect', 1, 'admin_center', '消費生活センター 188', 1.00, 'always',
 '「○○（製品名）に欠陥があり、メーカー／販売店との交渉を希望します」',
 ARRAY['購入契約書・領収書','製品欠陥の証拠（写真・動画・ログ・ハッシュ）','メーカーとのやり取り履歴'],
 '事業者への斡旋（あっせん）、PIO-NET データベースへの登録（再発防止）、行政指導の検討。',
 '事業者が応じない、または高度技術問題で対応困難 → tier 3 弁護士会',
 '188 は全国共通。地元の消費生活センターに自動接続。', 'curated_v1'),

('product_defect', 2, 'admin_center', '製品事故報告（NITE / 消費者庁）', 0.85, 'if_safety_risk',
 '「○○製品で事故が発生しました。再発防止のため報告します」',
 ARRAY['事故状況の写真・動画','製品識別情報（型番・製造番号・購入日）','医療記録（人身被害時）'],
 'NITE による技術調査、製品リコールの検討、消費者庁による行政指導。',
 '個別救済が必要 → tier 1 消費生活センター',
 '人身被害が出ている場合、消費生活用製品安全法に基づく重大事故報告は事業者の義務。', 'curated_v1'),

('product_defect', 3, 'bar_assoc', '弁護士会（PL法・製造物責任）', 0.85, 'if_money_lost_high',
 '「○○製品の欠陥により損害を被り、製造物責任法（PL法）に基づく損害賠償を検討しています」',
 ARRAY['購入証拠','欠陥の技術的証拠（できればフォレンジック解析データ・ハッシュチェーン）','損害額の根拠'],
 '内容証明送付／民事訴訟提起／和解交渉。',
 '和解不成立 → tier 4 民事訴訟／ADR（弁護士会仲裁センター）',
 '高度技術紛争は専門知識のある弁護士を選ぶこと。第二東京弁護士会 仲裁センター等の ADR が有効な場合あり。', 'curated_v1'),

('product_defect', 4, 'court', '弁護士会 仲裁センター（ADR）／簡裁・地裁', 0.75, 'always',
 '弁護士同伴。',
 ARRAY['弁護士が準備'],
 'ADR：和解あっせん（裁判より柔軟・低コスト）／地裁：判決による強制執行可能な救済。',
 '判決へ',
 'ADR は弁護士会仲裁センター（東京・大阪・名古屋等全国 35 か所）が利用可能。', 'curated_v1'),

('product_defect', 5, 'npo', 'CALL4・公共訴訟プラットフォーム', 0.65, 'if_collective',
 '「同種被害者が複数おり、公共訴訟として社会的に問題提起したい」',
 ARRAY['複数被害者の証言・データ','社会的影響の論点'],
 '訴訟の社会化、クラウドファンディング、メディア露出、構造的変革。',
 '判決後も継続的な政策提言',
 'CALL4 等。代理店被害・連続加害事案で有効。', 'curated_v1'),

-- foreign_worker ─────────────────────────────
('foreign_worker', 1, 'hotline', '外国人労働者向け相談ダイヤル 0570-011000', 1.00, 'always',
 '母国語可。「労働問題で相談したい」と伝える。',
 ARRAY['不要（電話のみ）'],
 '13 言語対応（厚労省）。労基署・FRESC への接続案内。',
 '即時対応必要 → tier 2',
 '厚生労働省委託。', 'curated_v1'),

('foreign_worker', 2, 'admin_center', '外国人在留総合インフォメーションセンター（FRESC）', 0.90, 'always',
 '「在留資格・労働問題を含めて総合相談したい」',
 ARRAY['在留カード','パスポート','労働契約書','給与明細'],
 '在留資格・労働・生活の総合ワンストップ支援（東京・大阪・名古屋等 6 拠点）。',
 '法的手続きが必要 → tier 4',
 '出入国在留管理庁。', 'curated_v1'),

('foreign_worker', 2, 'admin_center', '労働基準監督署', 0.85, 'if_wage_unpaid',
 '「賃金未払い／長時間労働／不当解雇／パスポート取り上げ等の被害を受けています」',
 ARRAY['労働契約書','給与明細・タイムカード','パスポート（取り上げ証拠）','日記・記録'],
 '事業主への調査・是正勧告／労基法違反の場合は刑事告発。',
 '民事救済 → tier 4',
 '通訳の手配は事前に依頼可能。', 'curated_v1'),

('foreign_worker', 3, 'npo', '移住者支援 NPO（POSSE・移住連・APFS 等）', 0.90, 'always',
 '母国語または英語で相談可能。',
 ARRAY['不要'],
 '同行支援／シェルター提供／法律相談接続／メディア接続。',
 '法的処理 → tier 4 弁護士会',
 '技能実習・特定技能・難民申請等、複合的な事案に強い。', 'curated_v1'),

('foreign_worker', 4, 'bar_assoc', '日本労働弁護団・各弁護士会（外国人支援委員会）', 0.80, 'if_evidence_strong',
 '英語・中国語・韓国語等の対応可能な弁護士を希望と伝える。',
 ARRAY['証拠一式'],
 '労働審判申立・地位確認訴訟・賃金請求訴訟。',
 '判決後の強制執行',
 '法テラス民事法律扶助の特例で外国人も利用可能（要件あり）。', 'curated_v1'),

-- admin_grievance ─────────────────────────────
('admin_grievance', 1, 'hotline', '法務省 みんなの人権 110番 0570-003-110', 1.00, 'always',
 '「行政手続きで不利益を受けた」「通報後に家族が機械的に分離された」等の状況を率直に。',
 ARRAY['不要'],
 '人権侵犯の調査開始可能性／関係機関への申し入れ。',
 '法的争いに発展 → tier 3',
 '法務省人権擁護局。匿名相談可。', 'curated_v1'),

('admin_grievance', 2, 'npo', '行政監視 NPO・社会福祉支援団体', 0.85, 'always',
 '「行政の機械的対応で生活が破綻している」「家族が分離された」等の具体状況を伝える。',
 ARRAY['行政処分の通知書','時系列メモ'],
 '同行支援／不服申立書類作成／メディア接続。',
 '法的争いへ → tier 3',
 'つくろい東京ファンド・POSSE・しんぐるまざあず・フォーラム等。', 'curated_v1'),

('admin_grievance', 3, 'admin_center', '行政不服審査会・各自治体オンブズマン', 0.75, 'if_official_decision',
 '「○○処分について、行政不服審査法に基づく審査請求をしたい」',
 ARRAY['行政処分の通知書','処分理由に対する反論メモ'],
 '審査請求の審理（書面）／処分の取消・変更可能性。',
 '却下されたら → tier 4 行政訴訟',
 '処分通知から 3 か月以内に申立必要。', 'curated_v1'),

('admin_grievance', 4, 'bar_assoc', '弁護士会（行政訴訟専門）', 0.70, 'if_evidence_strong',
 '「行政処分の取消訴訟／国家賠償請求を検討」',
 ARRAY['行政処分通知','審査請求の結果（あれば）','損害の根拠'],
 '取消訴訟・国家賠償請求訴訟。',
 '判決後',
 '行政事件訴訟法に基づく。費用：法テラス利用可。', 'curated_v1'),

('admin_grievance', 5, 'npo', 'CALL4 等公共訴訟プラットフォーム', 0.65, 'if_collective',
 '「同様の行政被害が他にもあり、構造的問題として提起したい」',
 ARRAY['複数被害事例'],
 '公共訴訟化／社会的議論／政策変更の可能性。',
 '判決後も政策提言継続',
 'CALL4 が日本の公共訴訟プラットフォーム。', 'curated_v1')
ON CONFLICT (category_code, tier, org_kind) DO UPDATE SET
  weight=EXCLUDED.weight, what_to_say_ja=EXCLUDED.what_to_say_ja,
  documents_needed_ja=EXCLUDED.documents_needed_ja,
  expected_outcome_ja=EXCLUDED.expected_outcome_ja,
  notes_ja=EXCLUDED.notes_ja;
