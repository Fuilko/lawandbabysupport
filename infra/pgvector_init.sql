-- LegalShield pgvector schema (Phase B)
--
-- 設計方針:
--   * embedding は VECTOR(384)（multilingual-e5-small）
--   * HNSW 索引（recall 高・線上 INSERT 可）
--   * metadata は分離カラム（court / year など）+ JSONB（拡張用）の併用
--   * cosine 距離（normalize 済み embeddings なので内積でも等価）

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- BM25-like fallback / metadata text search

-- ============================================================================
-- precedents（判例 ~724k）
-- ============================================================================
CREATE TABLE IF NOT EXISTS precedents (
    id              BIGSERIAL PRIMARY KEY,
    lawsuit_id      TEXT,
    case_number     TEXT,
    case_name       TEXT,
    court_name      TEXT,
    trial_type      TEXT,
    era             TEXT,
    year            INTEGER,
    month           INTEGER,
    day             INTEGER,
    chunk_index     INTEGER,
    text            TEXT NOT NULL,
    detail_link     TEXT,
    pdf_link        TEXT,
    text_source     TEXT,
    embedding       VECTOR(384) NOT NULL,
    metadata        JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_precedents_lawsuit ON precedents(lawsuit_id);
CREATE INDEX IF NOT EXISTS idx_precedents_court ON precedents(court_name);
CREATE INDEX IF NOT EXISTS idx_precedents_year ON precedents(year);
-- HNSW 索引は ETL 完了後に CREATE する（INSERT 性能のため後付け）。
-- CREATE INDEX idx_precedents_embedding ON precedents
--   USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);

-- ============================================================================
-- statutes（法令 elaws_v2; 現状 100 行 / 計画 623k）
-- ============================================================================
CREATE TABLE IF NOT EXISTS statutes (
    id              BIGSERIAL PRIMARY KEY,
    law_id          TEXT,
    law_name        TEXT,
    article         TEXT,
    text            TEXT NOT NULL,
    embedding       VECTOR(384) NOT NULL,
    metadata        JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_statutes_law ON statutes(law_id);

-- ============================================================================
-- litigation（CALL4 + 裁判所書式 ~3.8k）
-- ============================================================================
CREATE TABLE IF NOT EXISTS litigation (
    id              BIGSERIAL PRIMARY KEY,
    chunk_id        TEXT,
    source_type     TEXT,
    source_id       TEXT,
    chunk_idx       INTEGER,
    category        TEXT,
    title           TEXT,
    source_url      TEXT,
    text            TEXT NOT NULL,
    embedding       VECTOR(384) NOT NULL,
    metadata        JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_litigation_category ON litigation(category);

-- ============================================================================
-- ETL 進捗ログ（再開可能な ETL のために）
-- ============================================================================
CREATE TABLE IF NOT EXISTS etl_progress (
    table_name      TEXT PRIMARY KEY,
    last_offset     BIGINT NOT NULL DEFAULT 0,
    total_expected  BIGINT,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    notes           TEXT
);
