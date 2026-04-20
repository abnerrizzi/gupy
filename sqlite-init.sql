-- 1. BASE SCHEMA INITIALIZATION
-- Create the persistent "all" tables if they don't exist yet.
BEGIN;

CREATE TABLE IF NOT EXISTS jobs_all (
    id TEXT,
    company_id TEXT,
    title TEXT,
    type TEXT,
    department TEXT,
    workplace_city TEXT,
    workplace_state TEXT,
    workplace_type TEXT,
    source TEXT,
    run_ts TEXT,
    PRIMARY KEY (id, run_ts)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_jobs_id ON jobs_all(id);
CREATE INDEX IF NOT EXISTS idx_jobs_run_ts ON jobs_all(run_ts);
CREATE INDEX IF NOT EXISTS idx_jobs_company_id ON jobs_all(company_id);
CREATE INDEX IF NOT EXISTS idx_jobs_city ON jobs_all(workplace_city);
CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs_all(workplace_state);
CREATE INDEX IF NOT EXISTS idx_jobs_dept ON jobs_all(department);
CREATE INDEX IF NOT EXISTS idx_jobs_wp_type ON jobs_all(workplace_type);
CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs_all(type);
CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs_all(source);

CREATE TABLE IF NOT EXISTS companies_all (
    id TEXT,
    name TEXT,            
    logo_url TEXT,
    career_page_url TEXT,
    company_data TEXT,
    source TEXT,
    run_ts TEXT,
    PRIMARY KEY (id, run_ts)
);

CREATE INDEX IF NOT EXISTS idx_companies_id ON companies_all(id);
CREATE INDEX IF NOT EXISTS idx_companies_run_ts ON companies_all(run_ts);

-- 2. HANDLE TEMPORARY/TIMESTAMPED TABLES
-- We always create these to avoid "no such table" errors in subsequent steps.
-- If ${ts} is 0, these are just dummy tables for initialization.
CREATE TABLE IF NOT EXISTS jobs_${ts} (
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

CREATE TABLE IF NOT EXISTS companies_${ts} (
    id TEXT PRIMARY KEY,
    name TEXT,            
    logo_url TEXT,
    career_page_url TEXT,
    company_data TEXT,
    source TEXT
);

-- 3. DATA MIGRATION
-- Migration from current run to 'all' tables
-- If ${ts} is 0, this does nothing.
INSERT OR REPLACE INTO jobs_all 
SELECT *, '${ts}' as run_ts FROM jobs_${ts} WHERE '${ts}' != '0';

INSERT OR REPLACE INTO companies_all 
SELECT *, '${ts}' as run_ts FROM companies_${ts} WHERE '${ts}' != '0';

-- 4. UPDATE VIEWS
-- Views now point to the "latest" data within the "all" tables
DROP VIEW IF EXISTS jobs;
CREATE VIEW jobs AS 
SELECT * FROM jobs_all 
WHERE run_ts = (SELECT MAX(run_ts) FROM jobs_all);

DROP VIEW IF EXISTS companies;
CREATE VIEW companies AS 
SELECT * FROM companies_all 
WHERE run_ts = (SELECT MAX(run_ts) FROM companies_all);

-- Create or replace the "latest" tables for legacy compatibility
DROP TABLE IF EXISTS jobs_latest;
CREATE TABLE jobs_latest AS SELECT * FROM jobs;

DROP TABLE IF EXISTS companies_latest;
CREATE TABLE companies_latest AS SELECT * FROM companies;

-- Create the main job_details view
-- We use LEFT JOIN to ensure jobs are visible even if company data is missing
-- We use rtrim to avoid double slashes in URLs
DROP VIEW IF EXISTS job_details;
CREATE VIEW job_details AS
    SELECT
        j.id AS job_id,
        j.company_id,
        j.title AS job_title,
        COALESCE(c.name, j.company_id) AS company_name,
        -- Construct job URLs safely based on source
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
            ELSE 
                COALESCE(rtrim(c.career_page_url, '/'), '') || '/jobs/' || j.id
        END AS job_url,
        j.department AS job_department,
        j.type AS job_type,
        j.workplace_type AS workplace_type,
        j.workplace_city,
        j.workplace_state,
        j.source
    FROM
        jobs j
    LEFT JOIN
        companies c ON j.company_id = c.id;

COMMIT;

-- 5. ANALYTICS
-- Summary statistics
SELECT '----------------------------------------------' WHERE '${ts}' != '0';
SELECT 
    printf('%d jobs scraped from %d companies', 
        (SELECT COUNT(*) FROM jobs_${ts}), 
        (SELECT COUNT(*) FROM companies_${ts})
    ) AS result WHERE '${ts}' != '0';

SELECT '----------------------------------------------';
SELECT
    printf('Total: %d companies and %d jobs in the database', 
        (SELECT COUNT(*) FROM companies_all), 
        (SELECT COUNT(*) FROM jobs_all)
    ) AS total_count;
