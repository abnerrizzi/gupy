DROP TABLE IF EXISTS companies;
DROP TABLE IF EXISTS jobs;

.separator ";"
.mode csv
.import ${ts}-companies.csv companies
.import ${ts}-jobs.csv jobs

SELECT 
    printf('%d jobs scrapped from %d companies', 
        (SELECT COUNT(*) FROM jobs), 
        (SELECT COUNT(*) FROM companies)
    ) AS result;

SELECT '${ts}-gupy_from_csv.db' as out_file;
