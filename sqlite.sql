DROP TABLE IF EXISTS companies;
DROP TABLE IF EXISTS jobs;
-- DROP VIEW IF EXISTS v1;

CREATE TABLE "jobs"(
    "id" INT,
    "company_id" INT,
    "title" TEXT,
    "type" TEXT,
    "department" TEXT,
    "workplace_city" TEXT,
    "workplace_state" TEXT,
    "workplace_type" TEXT
);

CREATE TABLE "companies"(
    "id" INT,
    "name" TEXT,
    "logo_url" TEXT,
    "career_page_url" TEXT,
    "friendly_badge" TEXT
);


.separator ";"
.mode csv
.import companies.csv companies
.import jobs.csv jobs


.schema companies
.schema jobs
