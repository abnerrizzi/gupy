-- 1. BASE SCHEMA INITIALIZATION
-- Per-source "latest" tables are the source of truth. `jobs_all` / `companies_all`
-- are VIEWs that UNION ALL these per-source tables, so the API can keep reading
-- `jobs_all` / `companies_all` unchanged.
BEGIN;

-- 1a. Per-source LATEST tables (persistent, source of truth)
CREATE TABLE IF NOT EXISTS jobs_gupy_latest (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    title TEXT,
    type TEXT,
    department TEXT,
    workplace_city TEXT,
    workplace_state TEXT,
    workplace_type TEXT,
    source TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_gupy_company_id ON jobs_gupy_latest(company_id);
CREATE INDEX IF NOT EXISTS idx_jobs_gupy_city ON jobs_gupy_latest(workplace_city);
CREATE INDEX IF NOT EXISTS idx_jobs_gupy_state ON jobs_gupy_latest(workplace_state);
CREATE INDEX IF NOT EXISTS idx_jobs_gupy_dept ON jobs_gupy_latest(department);
CREATE INDEX IF NOT EXISTS idx_jobs_gupy_wp_type ON jobs_gupy_latest(workplace_type);
CREATE INDEX IF NOT EXISTS idx_jobs_gupy_type ON jobs_gupy_latest(type);
CREATE INDEX IF NOT EXISTS idx_jobs_gupy_source ON jobs_gupy_latest(source);

CREATE TABLE IF NOT EXISTS jobs_inhire_latest (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    title TEXT,
    type TEXT,
    department TEXT,
    workplace_city TEXT,
    workplace_state TEXT,
    workplace_type TEXT,
    source TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_inhire_company_id ON jobs_inhire_latest(company_id);
CREATE INDEX IF NOT EXISTS idx_jobs_inhire_city ON jobs_inhire_latest(workplace_city);
CREATE INDEX IF NOT EXISTS idx_jobs_inhire_state ON jobs_inhire_latest(workplace_state);
CREATE INDEX IF NOT EXISTS idx_jobs_inhire_dept ON jobs_inhire_latest(department);
CREATE INDEX IF NOT EXISTS idx_jobs_inhire_wp_type ON jobs_inhire_latest(workplace_type);
CREATE INDEX IF NOT EXISTS idx_jobs_inhire_type ON jobs_inhire_latest(type);
CREATE INDEX IF NOT EXISTS idx_jobs_inhire_source ON jobs_inhire_latest(source);

CREATE TABLE IF NOT EXISTS jobs_linkedin_latest (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    title TEXT,
    type TEXT,
    department TEXT,
    workplace_city TEXT,
    workplace_state TEXT,
    workplace_type TEXT,
    source TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_linkedin_company_id ON jobs_linkedin_latest(company_id);
CREATE INDEX IF NOT EXISTS idx_jobs_linkedin_city ON jobs_linkedin_latest(workplace_city);
CREATE INDEX IF NOT EXISTS idx_jobs_linkedin_state ON jobs_linkedin_latest(workplace_state);
CREATE INDEX IF NOT EXISTS idx_jobs_linkedin_dept ON jobs_linkedin_latest(department);
CREATE INDEX IF NOT EXISTS idx_jobs_linkedin_wp_type ON jobs_linkedin_latest(workplace_type);
CREATE INDEX IF NOT EXISTS idx_jobs_linkedin_type ON jobs_linkedin_latest(type);
CREATE INDEX IF NOT EXISTS idx_jobs_linkedin_source ON jobs_linkedin_latest(source);

CREATE TABLE IF NOT EXISTS companies_gupy_latest (
    id TEXT PRIMARY KEY,
    name TEXT,
    logo_url TEXT,
    career_page_url TEXT,
    company_data TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS companies_inhire_latest (
    id TEXT PRIMARY KEY,
    name TEXT,
    logo_url TEXT,
    career_page_url TEXT,
    company_data TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS companies_linkedin_latest (
    id TEXT PRIMARY KEY,
    name TEXT,
    logo_url TEXT,
    career_page_url TEXT,
    company_data TEXT,
    source TEXT
);

-- 1b. Per-source DETAIL tables (populated on demand by the API, one row per job
-- whose description has been fetched). Schema is source-specific because each
-- source ships a different payload shape; using one unified table would be
-- either sparse or stringly-typed.
CREATE TABLE IF NOT EXISTS jobs_gupy_detail (
    id TEXT PRIMARY KEY,
    description_html TEXT,
    responsibilities_html TEXT,
    prerequisites_html TEXT,
    workplace_type TEXT,
    job_type TEXT,
    country TEXT,
    published_at TEXT,
    next_data TEXT,
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs_inhire_detail (
    id TEXT PRIMARY KEY,
    description_html TEXT,
    about_html TEXT,
    contract_type TEXT,
    workplace_type TEXT,
    location TEXT,
    location_complement TEXT,
    published_at TEXT,
    raw_payload TEXT,
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs_linkedin_detail (
    id TEXT PRIMARY KEY,
    description TEXT,
    seniority TEXT,
    employment_type TEXT,
    job_function TEXT,
    industries TEXT,
    posted_at TEXT,
    num_applicants INTEGER,
    detail_html TEXT,
    fetched_at TEXT NOT NULL
);

-- 2. HANDLE TEMPORARY/TIMESTAMPED TABLES
-- Created for all three sources so the migration step below is a simple
-- per-source INSERT ... SELECT. If ${ts} is 0, these are dummy init tables.
CREATE TABLE IF NOT EXISTS jobs_gupy_${ts} (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    title TEXT,
    type TEXT,
    department TEXT,
    workplace_city TEXT,
    workplace_state TEXT,
    workplace_type TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS jobs_inhire_${ts} (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    title TEXT,
    type TEXT,
    department TEXT,
    workplace_city TEXT,
    workplace_state TEXT,
    workplace_type TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS jobs_linkedin_${ts} (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    title TEXT,
    type TEXT,
    department TEXT,
    workplace_city TEXT,
    workplace_state TEXT,
    workplace_type TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS companies_gupy_${ts} (
    id TEXT PRIMARY KEY,
    name TEXT,
    logo_url TEXT,
    career_page_url TEXT,
    company_data TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS companies_inhire_${ts} (
    id TEXT PRIMARY KEY,
    name TEXT,
    logo_url TEXT,
    career_page_url TEXT,
    company_data TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS companies_linkedin_${ts} (
    id TEXT PRIMARY KEY,
    name TEXT,
    logo_url TEXT,
    career_page_url TEXT,
    company_data TEXT,
    source TEXT
);

-- 3. DATA MIGRATION
-- Per-source merge from current run timestamped tables into latest tables.
-- If ${ts} is 0, these are no-ops. When ${<source>_mode} is 'replace', the
-- _latest table is wiped first so the current run becomes the authoritative
-- snapshot (IDs absent from this run are dropped). The EXISTS guard ensures
-- an empty/failed run never wipes previously-good data.
DELETE FROM jobs_gupy_latest
WHERE '${gupy_mode}' = 'replace'
  AND '${ts}' != '0'
  AND EXISTS (SELECT 1 FROM jobs_gupy_${ts} LIMIT 1);
INSERT OR REPLACE INTO jobs_gupy_latest
SELECT * FROM jobs_gupy_${ts} WHERE '${ts}' != '0';

DELETE FROM jobs_inhire_latest
WHERE '${inhire_mode}' = 'replace'
  AND '${ts}' != '0'
  AND EXISTS (SELECT 1 FROM jobs_inhire_${ts} LIMIT 1);
INSERT OR REPLACE INTO jobs_inhire_latest
SELECT * FROM jobs_inhire_${ts} WHERE '${ts}' != '0';

DELETE FROM jobs_linkedin_latest
WHERE '${linkedin_mode}' = 'replace'
  AND '${ts}' != '0'
  AND EXISTS (SELECT 1 FROM jobs_linkedin_${ts} LIMIT 1);
INSERT OR REPLACE INTO jobs_linkedin_latest
SELECT * FROM jobs_linkedin_${ts} WHERE '${ts}' != '0';

DELETE FROM companies_gupy_latest
WHERE '${gupy_mode}' = 'replace'
  AND '${ts}' != '0'
  AND EXISTS (SELECT 1 FROM companies_gupy_${ts} LIMIT 1);
INSERT OR REPLACE INTO companies_gupy_latest
SELECT * FROM companies_gupy_${ts} WHERE '${ts}' != '0';

DELETE FROM companies_inhire_latest
WHERE '${inhire_mode}' = 'replace'
  AND '${ts}' != '0'
  AND EXISTS (SELECT 1 FROM companies_inhire_${ts} LIMIT 1);
INSERT OR REPLACE INTO companies_inhire_latest
SELECT * FROM companies_inhire_${ts} WHERE '${ts}' != '0';

DELETE FROM companies_linkedin_latest
WHERE '${linkedin_mode}' = 'replace'
  AND '${ts}' != '0'
  AND EXISTS (SELECT 1 FROM companies_linkedin_${ts} LIMIT 1);
INSERT OR REPLACE INTO companies_linkedin_latest
SELECT * FROM companies_linkedin_${ts} WHERE '${ts}' != '0';

-- 4. VIEWS
-- `jobs_all` / `companies_all` are unioned views; the API reads these as if
-- they were tables. SQLite resolves SELECT/JOIN through views transparently.
DROP VIEW IF EXISTS jobs_all;
CREATE VIEW jobs_all AS
    SELECT * FROM jobs_gupy_latest
    UNION ALL
    SELECT * FROM jobs_inhire_latest
    UNION ALL
    SELECT * FROM jobs_linkedin_latest;

DROP VIEW IF EXISTS companies_all;
CREATE VIEW companies_all AS
    SELECT * FROM companies_gupy_latest
    UNION ALL
    SELECT * FROM companies_inhire_latest
    UNION ALL
    SELECT * FROM companies_linkedin_latest;

DROP VIEW IF EXISTS jobs;
CREATE VIEW jobs AS SELECT * FROM jobs_all;

DROP VIEW IF EXISTS companies;
CREATE VIEW companies AS SELECT * FROM companies_all;

-- Legacy "latest" shadow names recreated as views. Pre-split TABLE case is
-- handled by migrate-to-per-source.sql before this script runs.
DROP VIEW IF EXISTS jobs_latest;
CREATE VIEW jobs_latest AS SELECT * FROM jobs_all;

DROP VIEW IF EXISTS companies_latest;
CREATE VIEW companies_latest AS SELECT * FROM companies_all;

DROP VIEW IF EXISTS job_details;
CREATE VIEW job_details AS
    SELECT
        j.id AS job_id,
        j.company_id,
        j.title AS job_title,
        COALESCE(c.name, j.company_id) AS company_name,
        CASE
            WHEN j.source = 'gupy' THEN
                CASE
                    WHEN c.career_page_url LIKE '%/%' THEN
                        substr(c.career_page_url, 1, instr(substr(c.career_page_url, 9), '/') + 8) || 'jobs/' || j.id
                    WHEN c.career_page_url IS NOT NULL THEN
                        rtrim(c.career_page_url, '/') || '/jobs/' || j.id
                    ELSE 'https://portal.gupy.io/job/' || j.id
                END
            WHEN j.source = 'inhire' THEN
                'https://' || j.company_id || '.inhire.app/vagas/' || j.id || '/description'
            WHEN j.source = 'linkedin' THEN
                'https://www.linkedin.com/jobs/view/' || j.id
            ELSE
                COALESCE(rtrim(c.career_page_url, '/'), '') || '/jobs/' || j.id
        END AS job_url,
        j.department AS job_department,
        j.type AS job_type,
        j.workplace_type AS workplace_type,
        j.workplace_city,
        j.workplace_state,
        j.source,
        CASE j.source
            WHEN 'gupy'     THEN CASE WHEN gd.id IS NOT NULL THEN 1 ELSE 0 END
            WHEN 'inhire'   THEN CASE WHEN ih.id IS NOT NULL THEN 1 ELSE 0 END
            WHEN 'linkedin' THEN CASE WHEN ld.id IS NOT NULL THEN 1 ELSE 0 END
            ELSE 0
        END AS has_detail,
        COALESCE(gd.fetched_at, ih.fetched_at, ld.fetched_at) AS detail_fetched_at
    FROM
        jobs_all j
    LEFT JOIN
        companies_all c ON j.company_id = c.id
    LEFT JOIN
        jobs_gupy_detail gd ON j.source = 'gupy' AND gd.id = j.id
    LEFT JOIN
        jobs_inhire_detail ih ON j.source = 'inhire' AND ih.id = j.id
    LEFT JOIN
        jobs_linkedin_detail ld ON j.source = 'linkedin' AND ld.id = j.id;

-- 4. APP STATE (auth + tracker)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

COMMIT;

-- 5. ANALYTICS
SELECT '----------------------------------------------' WHERE '${ts}' != '0';
SELECT
    printf('%d jobs scraped from %d companies (this run)',
        (SELECT COUNT(*) FROM jobs_gupy_${ts})
            + (SELECT COUNT(*) FROM jobs_inhire_${ts})
            + (SELECT COUNT(*) FROM jobs_linkedin_${ts}),
        (SELECT COUNT(*) FROM companies_gupy_${ts})
            + (SELECT COUNT(*) FROM companies_inhire_${ts})
            + (SELECT COUNT(*) FROM companies_linkedin_${ts})
    ) AS result WHERE '${ts}' != '0';

SELECT '----------------------------------------------';
SELECT
    printf('Total: %d companies and %d jobs across all sources',
        (SELECT COUNT(*) FROM companies_all),
        (SELECT COUNT(*) FROM jobs_all)
    ) AS total_count;
