-- One-shot migration: pre-split DBs had `jobs_all` / `companies_all` as TABLES.
-- This script redistributes their rows into per-source `_latest` tables and drops
-- the old tables so sqlite-init.sql can recreate them as UNION views.
-- Idempotent-guarded by run_scrap.sh (only invoked when jobs_all is a table).
BEGIN;

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

-- Redistribute rows by source
INSERT OR REPLACE INTO jobs_gupy_latest
    SELECT id, company_id, title, type, department,
           workplace_city, workplace_state, workplace_type, source
    FROM jobs_all WHERE source = 'gupy';

INSERT OR REPLACE INTO jobs_inhire_latest
    SELECT id, company_id, title, type, department,
           workplace_city, workplace_state, workplace_type, source
    FROM jobs_all WHERE source = 'inhire';

INSERT OR REPLACE INTO jobs_linkedin_latest
    SELECT id, company_id, title, type, department,
           workplace_city, workplace_state, workplace_type, source
    FROM jobs_all WHERE source = 'linkedin';

INSERT OR REPLACE INTO companies_gupy_latest
    SELECT id, name, logo_url, career_page_url, company_data, source
    FROM companies_all WHERE source = 'gupy';

INSERT OR REPLACE INTO companies_inhire_latest
    SELECT id, name, logo_url, career_page_url, company_data, source
    FROM companies_all WHERE source = 'inhire';

INSERT OR REPLACE INTO companies_linkedin_latest
    SELECT id, name, logo_url, career_page_url, company_data, source
    FROM companies_all WHERE source = 'linkedin';

-- Drop legacy shadow tables and views that depend on the old _all tables
DROP TABLE IF EXISTS jobs_latest;
DROP TABLE IF EXISTS companies_latest;
DROP VIEW IF EXISTS job_details;
DROP VIEW IF EXISTS jobs;
DROP VIEW IF EXISTS companies;

-- Drop the old tables (sqlite-init.sql will recreate them as UNION views)
DROP TABLE jobs_all;
DROP TABLE companies_all;

COMMIT;
