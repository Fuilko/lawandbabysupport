-- LegalShield-jp DB schema (PostgreSQL 15+ with PostGIS 3.3+).
-- Idempotent — safe to re-run.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS pgcrypto;        -- gen_random_uuid for incident reports
-- pgvector is optional; uncomment if you ship semantic search later.
-- CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS legalshield;

-- ─────────────────────────────────────────────────────────────
-- support_org : 法テラス + NPO + NGO + 弁護士会 (unified)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS legalshield.support_org (
  id              BIGSERIAL PRIMARY KEY,
  org_type        TEXT NOT NULL CHECK (org_type IN
                    ('law_terrace','npo','ngo','bar_association','other')),
  name            TEXT NOT NULL,
  prefecture_code CHAR(2),                      -- JIS X 0401 (e.g. '13' = Tokyo)
  city_code       CHAR(5),                      -- JIS X 0402
  address         TEXT,
  geom            GEOGRAPHY(POINT, 4326),
  services        TEXT[] DEFAULT '{}',          -- ['domestic_violence','child_protection',...]
  contact         JSONB DEFAULT '{}'::jsonb,    -- {phone, fax, url, email, hours}
  source          TEXT NOT NULL,                -- 'houterasu' | 'cao_npo' | ...
  source_url      TEXT,
  source_id       TEXT,                         -- upstream natural key (UNIQUE within source)
  last_synced     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (source, source_id)
);
CREATE INDEX IF NOT EXISTS idx_support_org_geom
  ON legalshield.support_org USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_support_org_type
  ON legalshield.support_org (org_type);
CREATE INDEX IF NOT EXISTS idx_support_org_prefecture
  ON legalshield.support_org (prefecture_code);
CREATE INDEX IF NOT EXISTS idx_support_org_services
  ON legalshield.support_org USING GIN (services);

-- ─────────────────────────────────────────────────────────────
-- prefecture / city boundaries from 国土数値情報 N03
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS legalshield.prefecture (
  prefecture_code CHAR(2)  PRIMARY KEY,         -- '01' Hokkaido ... '47' Okinawa
  name_ja         TEXT     NOT NULL,
  name_en         TEXT,
  geom            GEOGRAPHY(MULTIPOLYGON, 4326),
  population      BIGINT,                       -- 国勢調査 latest
  area_km2        DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_prefecture_geom
  ON legalshield.prefecture USING GIST (geom);

CREATE TABLE IF NOT EXISTS legalshield.city (
  city_code       CHAR(5)  PRIMARY KEY,         -- JIS X 0402
  prefecture_code CHAR(2)  NOT NULL REFERENCES legalshield.prefecture(prefecture_code),
  name_ja         TEXT     NOT NULL,
  geom            GEOGRAPHY(MULTIPOLYGON, 4326)
);
CREATE INDEX IF NOT EXISTS idx_city_geom
  ON legalshield.city USING GIST (geom);

-- ─────────────────────────────────────────────────────────────
-- crime_grid : 500 m square grid x year-month x crime category
-- grid_id format: 'JIS-{prefcode}-500-{x}-{y}'  (custom QGIS-compatible)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS legalshield.crime_grid (
  grid_id     TEXT     NOT NULL,
  geom        GEOGRAPHY(POLYGON, 4326) NOT NULL,
  year_month  CHAR(7)  NOT NULL,                -- 'YYYY-MM'
  total_count INTEGER  NOT NULL DEFAULT 0,
  by_type     JSONB    NOT NULL DEFAULT '{}'::jsonb,
  prefecture_code CHAR(2),
  PRIMARY KEY (grid_id, year_month)
);
CREATE INDEX IF NOT EXISTS idx_crime_grid_geom
  ON legalshield.crime_grid USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_crime_grid_ym
  ON legalshield.crime_grid (year_month);

-- Convenience materialized view: 12-month rolling crime density per grid.
-- Refresh nightly with REFRESH MATERIALIZED VIEW CONCURRENTLY.
CREATE MATERIALIZED VIEW IF NOT EXISTS legalshield.crime_grid_12m AS
SELECT
  grid_id,
  MIN(prefecture_code)         AS prefecture_code,
  ST_Union(geom::geometry)::geography AS geom,
  SUM(total_count)             AS total_12m
FROM legalshield.crime_grid
WHERE year_month >= TO_CHAR(NOW() - INTERVAL '12 months', 'YYYY-MM')
GROUP BY grid_id;
CREATE UNIQUE INDEX IF NOT EXISTS idx_crime_grid_12m_pk
  ON legalshield.crime_grid_12m (grid_id);
CREATE INDEX IF NOT EXISTS idx_crime_grid_12m_geom
  ON legalshield.crime_grid_12m USING GIST (geom);

-- ─────────────────────────────────────────────────────────────
-- incident_report : anonymous user-submitted events
-- geom (real coords)         → server-side internal use only, never returned via API
-- obfuscated_geom (polygon)  → public-safe: random offset 100-300 m
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS legalshield.incident_report (
  id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  geom            GEOGRAPHY(POINT, 4326) NOT NULL,
  obfuscated_geom GEOGRAPHY(POLYGON, 4326) NOT NULL,
  incident_type   TEXT         NOT NULL,
  description     TEXT,
  reported_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  client_hash     TEXT,                         -- optional rate-limit key (sha256 of IP+UA, never raw)
  is_published    BOOLEAN      NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_incident_obfuscated_geom
  ON legalshield.incident_report USING GIST (obfuscated_geom);
CREATE INDEX IF NOT EXISTS idx_incident_reported_at
  ON legalshield.incident_report (reported_at DESC);

-- ─────────────────────────────────────────────────────────────
-- ingest_run : observability for ETL pipeline
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS legalshield.ingest_run (
  id          BIGSERIAL PRIMARY KEY,
  dataset     TEXT NOT NULL,
  started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  status      TEXT NOT NULL DEFAULT 'running',  -- 'running' | 'success' | 'failed'
  rows_in     INTEGER,
  rows_out    INTEGER,
  notes       TEXT
);
