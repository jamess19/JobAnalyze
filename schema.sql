-- ====================================================
-- 1. EXTENSIONS & SETUP
-- ====================================================
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ====================================================
-- 2. DIMENSION TABLES
-- ====================================================

-- 2.1 LOCATIONS
CREATE TABLE IF NOT EXISTS locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    city_name TEXT UNIQUE, -- Cần UNIQUE để tránh duplicate location
    country TEXT DEFAULT 'Vietnam',
    raw_name TEXT -- Lưu tên gốc để debug
);

-- 2.2 SKILLS
CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL, -- "ReactJS" (Đã chuẩn hóa)
    category TEXT              -- "Framework", "Language"
);

-- 2.3 DOMAIN (Mới thêm theo sơ đồ)
CREATE TABLE IF NOT EXISTS domains (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL -- "Fintech", "E-commerce"
);

-- ====================================================
-- 3. HYPERTABLES (Bảng dữ liệu chính)
-- ====================================================

-- 3.1 JOBS
CREATE TABLE IF NOT EXISTS jobs (
    -- Định danh & Thời gian
    id UUID NOT NULL,
    posted_date TIMESTAMP NOT NULL, -- Partition Key
    
    -- Metadata
    source TEXT DEFAULT 'web scrape',
    title TEXT,
    company_name TEXT,
    url TEXT, -- Link gốc
    
    -- Dữ liệu cần làm sạch (Cleaning needed)
    salary_min DECIMAL(15, 2),
    salary_max DECIMAL(15, 2),
    salary_currency TEXT DEFAULT 'VND',
    experience TEXT, -- Lưu dạng chuỗi trước, chuẩn hóa sau
    
    -- Khóa ngoại
    location_id UUID REFERENCES locations(id),
    
    -- Hệ thống
    processed_at TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW(), -- Dùng cho Deduplication
    
    -- BẮT BUỘC: Composite Primary Key cho TimescaleDB
    PRIMARY KEY (id, posted_date)
);

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS minhash_signature INTEGER[];
-- Biến thành Hypertable
SELECT create_hypertable('jobs', 'posted_date', if_not_exists => TRUE);

-- 3.2 JOB_SKILLS (Quan hệ Job - Skill)
CREATE TABLE IF NOT EXISTS job_skills (
    job_id UUID NOT NULL,
    skill_id UUID NOT NULL REFERENCES skills(id),
    posted_date TIMESTAMP NOT NULL, -- Copy từ jobs để partition
    
    PRIMARY KEY (job_id, skill_id, posted_date)
);
SELECT create_hypertable('job_skills', 'posted_date', if_not_exists => TRUE);

-- 3.3 JOB_DOMAIN (Quan hệ Job - Domain - Mới thêm)
CREATE TABLE IF NOT EXISTS job_domain (
    job_id UUID NOT NULL,
    domain_id UUID NOT NULL REFERENCES domains(id),
    posted_date TIMESTAMP NOT NULL, -- Copy từ jobs
    
    PRIMARY KEY (job_id, domain_id, posted_date)
);
SELECT create_hypertable('job_domain', 'posted_date', if_not_exists => TRUE);

-- ====================================================
-- 4. TECHNICAL TABLES (Bảng kỹ thuật - Không có trong ERD nhưng cần thiết)
-- ====================================================

-- Bảng này dùng cho thuật toán MinHash LSH
CREATE TABLE IF NOT EXISTS lsh_buckets (
    band_idx INTEGER NOT NULL,
    bucket_hash VARCHAR(64) NOT NULL,
    job_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Index để query cực nhanh
    PRIMARY KEY (band_idx, bucket_hash, job_id)
);
CREATE INDEX IF NOT EXISTS idx_lsh_lookup ON lsh_buckets(band_idx, bucket_hash);

-- ====================================================
-- 5. CONTINUOUS AGGREGATES (Thống kê tự động)
-- ====================================================

-- 5.1 SKILL STATS
CREATE MATERIALIZED VIEW IF NOT EXISTS skill_daily_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', posted_date) AS date,
    skill_id,
    COUNT(job_id) AS job_count
FROM job_skills
GROUP BY date, skill_id;

-- 5.2 DOMAIN STATS (Mới thêm)
CREATE MATERIALIZED VIEW IF NOT EXISTS domain_daily_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', posted_date) AS date,
    domain_id,
    COUNT(job_id) AS job_count
FROM job_domain
GROUP BY date, domain_id;

-- ====================================================
-- 6. POLICIES (Tự động cập nhật View)
-- ====================================================
SELECT add_continuous_aggregate_policy('skill_daily_stats',
    start_offset => INTERVAL '1 month',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '2 hours');

SELECT add_continuous_aggregate_policy('domain_daily_stats',
    start_offset => INTERVAL '1 month',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '2 hours');

-- ====================================================
-- 7. AI MARKET INSIGHTS — READ-ONLY ROLE
-- ====================================================
-- Used by src/ai/insight_engine.py to execute LLM-generated SQL.
-- This role is the real security boundary for that feature (not the
-- app-level guard in sql_guard.py): even if a generated query slips
-- past the guard, this role physically cannot INSERT/UPDATE/DELETE/DROP.
-- Change the password below before using this outside a local demo.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'ai_readonly') THEN
        CREATE ROLE ai_readonly WITH LOGIN PASSWORD 'ai_readonly_change_me';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE job_market TO ai_readonly;
GRANT USAGE ON SCHEMA public TO ai_readonly;
GRANT SELECT ON
    jobs, locations, skills, domains,
    job_skills, job_domain,
    skill_daily_stats, domain_daily_stats
TO ai_readonly;
-- No INSERT/UPDATE/DELETE/DDL privileges are ever granted to this role.

-- Read-only doesn't mean cheap: a single expensive SELECT (recursive CTE,
-- unconstrained cross join, pg_sleep()) can still exhaust the DB. Cap it.
ALTER ROLE ai_readonly SET statement_timeout = '5s';