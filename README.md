use this query to return the list:

```sql
SELECT 
    c.name as company,
    j.title,
    SUBSTR(c.career_page_url, 1, LENGTH(c.career_page_url) - INSTR(REVERSE(c.career_page_url), '/') + 1) || "jobs/" || j.id AS concatenated_field,
    j.type,
    j.workplace_type 
FROM 
    jobs j
JOIN 
    companies c ON c.id = j.company_id
WHERE 1=1
;
