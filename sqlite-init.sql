-- SQLite initialization script for direct database approach
-- This script applies post-processing steps after data has been inserted

-- Drop existing view if it exists
DROP VIEW IF EXISTS job_details;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_jobs_company_id ON jobs(company_id);
CREATE INDEX IF NOT EXISTS idx_companies_id ON companies(id);

-- Create the main view
CREATE VIEW job_details AS
    SELECT
        j.id AS job_id,
        c.id AS company_id,
        j.title AS job_title,
        c.name AS company_name,
        substr(c.career_page_url, 1, 
            instr(substr(c.career_page_url, 9), '/') + 8) || 'jobs/' || j.id AS job_url,
        substr(c.career_page_url, 1, instr(substr(c.career_page_url, 9), '/') + 8) ||
            '_next/data/VX0nrGhF9_x9sbT1sYX09/pt/jobs/' || j.id || '.json'
                AS job_url_detail,
        j.department AS job_department,
        j.type AS job_type,
        j.workplace_type AS workplace_type,
        j.workplace_city,
        j.workplace_state
    FROM
        jobs j
    JOIN
        companies c ON j.company_id = c.id
    GROUP BY
        j.id, c.id
    ;

-- Data quality checks
SELECT 'Data Quality Report' as report_section;
SELECT 
    printf('Companies with missing career page URLs: %d', 
        (SELECT COUNT(*) FROM companies WHERE career_page_url IS NULL OR career_page_url = '')
    ) AS quality_check;

SELECT 
    printf('Jobs with missing company references: %d', 
        (SELECT COUNT(*) FROM jobs j LEFT JOIN companies c ON j.company_id = c.id WHERE c.id IS NULL)
    ) AS quality_check;

-- Summary statistics
SELECT 'Summary Statistics' as report_section;
SELECT 
    printf('%d jobs scraped from %d companies', 
        (SELECT COUNT(*) FROM jobs), 
        (SELECT COUNT(*) FROM companies)
    ) AS result;

-- Top departments by job count
SELECT 'Top Departments' as report_section;
SELECT 
    department,
    COUNT(*) as job_count
FROM jobs 
WHERE department != 'N/A'
GROUP BY department 
ORDER BY job_count DESC 
LIMIT 10;

-- Jobs by workplace type
SELECT 'Workplace Types' as report_section;
SELECT 
    workplace_type,
    COUNT(*) as job_count
FROM jobs 
GROUP BY workplace_type 
ORDER BY job_count DESC;

-- Output file confirmation
SELECT '${ts}-gupy_direct.db' as output_file;