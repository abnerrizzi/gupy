-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_jobs_company_id ON jobs_${ts}(company_id);
CREATE INDEX IF NOT EXISTS idx_companies_id ON companies_${ts}(id);


-- Create or replace the "latest" table
DROP TABLE IF EXISTS jobs_latest;
CREATE TABLE jobs_latest AS
SELECT * FROM jobs_${ts};

CREATE TABLE IF NOT EXISTS jobs_all AS SELECT * FROM jobs_${ts};
-- Create a view that merges latest + historical snapshot, removing duplicates
INSERT INTO jobs_all
SELECT * FROM jobs_${ts}
WHERE id NOT IN (SELECT id FROM jobs_all);



-- Create or replace the "latest" table
DROP TABLE IF EXISTS companies_latest;
CREATE TABLE companies_latest AS
SELECT * FROM companies_${ts};

CREATE TABLE IF NOT EXISTS companies_all AS SELECT * FROM companies_${ts};
-- Create a view that merges latest + historical snapshot, removing duplicates
INSERT INTO companies_all
SELECT * FROM companies_${ts}
WHERE id NOT IN (SELECT id FROM companies_all);







-- Create the main view
DROP VIEW IF EXISTS job_details;
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
        companies_${ts} c ON j.company_id = c.id
    GROUP BY
        j.id, c.id
    ;

-- Data quality checks
SELECT '----------------------------------------------' as line_breaker;
SELECT 
    printf('Companies with missing career page URLs: %d', 
        (SELECT COUNT(*) FROM companies_${ts} WHERE career_page_url IS NULL OR career_page_url = '')
    ) AS quality_check;

SELECT 
    printf('Jobs with missing company references: %d', 
        (SELECT COUNT(*) FROM jobs_${ts} j LEFT JOIN companies_${ts} c ON j.company_id = c.id WHERE c.id IS NULL)
    ) AS quality_check;

-- Summary statistics
SELECT 
    printf('%d jobs scraped from %d companies', 
        (SELECT COUNT(*) FROM jobs_${ts}), 
        (SELECT COUNT(*) FROM companies_${ts})
    ) AS result;

-- Total companies & jobs
SELECT '----------------------------------------------' as line_breaker;
SELECT
    printf('Total: %d companies and %d jobs in the database', 
        (SELECT COUNT(*) FROM companies_all), 
        (SELECT COUNT(*) FROM jobs_all)
    ) AS total_count;
-- Top departments by job count
SELECT '----------------------------------------------' as line_breaker;
SELECT 'Top 5 Departments' as report_section;
SELECT 
    department,
    COUNT(*) as job_count
FROM jobs_${ts} 
WHERE department != 'N/A'
GROUP BY department 
ORDER BY job_count DESC 
LIMIT 5;

-- Jobs by workplace type
SELECT '----------------------------------------------' as line_breaker;
SELECT 'Workplace Types' as report_section;
SELECT 
    workplace_type,
    COUNT(*) as job_count
FROM jobs_${ts} 
GROUP BY workplace_type 
ORDER BY job_count DESC;
