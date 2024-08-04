DROP TABLE IF EXISTS companies;
DROP TABLE IF EXISTS jobs;

.separator ";"
.mode csv
.import ${ts}-companies.csv companies
.import ${ts}-jobs.csv jobs

-- create view
CREATE VIEW job_details AS
    SELECT
        j.id AS job_id,
        c.id AS company_id,
        j.title AS job_title,
        c.name AS company_name,
        substr(c.career_page_url, 1, 
            instr(substr(c.career_page_url, 9), '/') + 8) || 'jobs/' || j.id AS job_url,
        j.department AS job_department,
        j.type AS job_type,
        j.workplace_type AS workplace_type
    FROM
        jobs j
    JOIN
        companies c ON j.company_id = c.id
    GROUP BY
        j.id, c.id;

-- printing output
SELECT 
    printf('%d jobs scrapped from %d companies', 
        (SELECT COUNT(*) FROM jobs), 
        (SELECT COUNT(*) FROM companies)
    ) AS result;
SELECT '${ts}-gupy_from_csv.db' as out_file;
