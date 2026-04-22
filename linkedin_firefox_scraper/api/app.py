#!/usr/bin/env python
import os
import sqlite3
import json
from flask import Flask, request, jsonify, g

app = Flask(__name__)

DATABASE = os.environ.get('JOBHUBMINE_DATABASE', '/app/out/jobhubmine.db')


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def row_to_dict(row):
    return dict(row) if row else None


def rows_to_list(rows):
    return [row_to_dict(row) for row in rows]


def build_filters(args):
    where_clauses = []
    params = []

    filters = {
        'search': ('j.title LIKE ?', lambda v: f'%{v}%'),
        'company_id': ('j.company_id = ?', None),
        'city': ('j.workplace_city = ?', None),
        'state': ('j.workplace_state = ?', None),
        'department': ('j.department = ?', None),
        'workplace_type': ('j.workplace_type = ?', None),
        'type': ('j.type = ?', None),
        'source': ('j.source = ?', None),
    }

    for arg_name, (clause, transform) in filters.items():
        if clause is None:
            continue
        value = args.get(arg_name)
        if value:
            where_clauses.append(clause)
            params.append(transform(value) if transform else value)

    wp_label = args.get('workplaceType')
    if wp_label:
        if wp_label == 'Presencial':
            where_clauses.append("LOWER(j.workplace_type) IN ('on-site', 'presencial')")
        elif wp_label == 'Remoto':
            where_clauses.append("LOWER(j.workplace_type) IN ('remote', 'remoto', 'home office')")
        elif wp_label == 'Híbrido':
            where_clauses.append("LOWER(j.workplace_type) IN ('hybrid', 'híbrido')")
        else:
            where_clauses.append("j.workplace_type = ?")
            params.append(wp_label)

    jt_label = args.get('jobType')
    if jt_label:
        if jt_label == 'Efetiva':
            where_clauses.append("LOWER(j.type) IN ('vacancy_type_effective', 'efetivo', 'full-time')")
        elif jt_label == 'Estágio':
            where_clauses.append("LOWER(j.type) IN ('vacancy_type_internship', 'estágio', 'internship')")
        elif jt_label == 'PJ':
            where_clauses.append("LOWER(j.type) IN ('vacancy_legal_entity', 'pj')")
        elif jt_label == 'Outros':
            where_clauses.append("(j.type IS NULL OR j.type = '' OR j.type = 'N/A')")
        else:
            where_clauses.append("j.type = ?")
            params.append(jt_label)

    where_str = ""
    if where_clauses:
        where_str = " AND " + " AND ".join(where_clauses)

    sort_mapping = {
        'job_title': 'j.title',
        'company_name': 'c.name',
        'workplace_city': 'j.workplace_city',
        'job_type': 'j.type',
        'workplace_type': 'j.workplace_type',
        'source': 'j.source'
    }

    sort_key = args.get('sort', 'job_title')
    sort_order = args.get('order', 'asc').lower()

    db_col = sort_mapping.get(sort_key, 'j.title')
    direction = 'ASC' if sort_order == 'asc' else 'DESC'
    order_str = f"ORDER BY {db_col} {direction}"

    return where_str, order_str, params


def safe_int(val, default, min_val=None, max_val=None):
    try:
        res = int(val)
        if min_val is not None:
            res = max(res, min_val)
        if max_val is not None:
            res = min(res, max_val)
        return res
    except (ValueError, TypeError):
        return default


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})


def get_job_url(job, company):
    source = job.get('source')
    job_id = job.get('id')

    if source == 'linkedin':
        return f"https://www.linkedin.com/jobs/view/{job_id}"

    if source == 'gupy':
        if company and company.get('career_page_url'):
            url = company['career_page_url']
            if '/' in url[8:]:
                base = url[:url.find('/', 8) + 1]
                return f"{base}jobs/{job_id}"
            return f"{url.rstrip('/')}/jobs/{job_id}"
        return f"https://portal.gupy.io/job/{job_id}"

    if source == 'inhire':
        tenant = job.get('company_id')
        return f"https://{tenant}.inhire.app/vagas/{job_id}/description"

    return ""


@app.route('/api/jobs')
def get_jobs():
    db = get_db()
    cursor = db.cursor()

    where_str, order_str, params = build_filters(request.args)

    query = f"""
        SELECT
            j.*,
            c.name as company_name,
            c.logo_url as company_logo,
            c.career_page_url as company_url
        FROM jobs_all j
        LEFT JOIN companies_all c ON j.company_id = c.id
        WHERE 1=1 {where_str}
    """

    limit = safe_int(request.args.get('limit'), 100, min_val=1, max_val=1000)
    offset = safe_int(request.args.get('offset'), 0, min_val=0)

    count_query = f"SELECT COUNT(*) FROM jobs_all j WHERE 1=1 {where_str}"

    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    query += f" {order_str} LIMIT ? OFFSET ?"
    query_params = params + [limit, offset]

    cursor.execute(query, query_params)
    rows = cursor.fetchall()
    jobs = []
    for row in rows:
        d = dict(row)
        d['job_id'] = d['id']
        d['job_title'] = d['title']
        d['job_department'] = d['department']
        d['job_type'] = d['type']
        company = {'career_page_url': d.get('company_url')}
        d['job_url'] = get_job_url(d, company)
        jobs.append(d)

    return jsonify({
        'jobs': jobs,
        'total': total,
        'limit': limit,
        'offset': offset
    })


@app.route('/api/companies')
def get_companies():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM companies_all ORDER BY name")
    companies = rows_to_list(cursor.fetchall())
    return jsonify({'companies': companies})


@app.route('/api/filters')
def get_filters():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT DISTINCT workplace_city FROM jobs_all WHERE workplace_city IS NOT NULL AND workplace_city != '' ORDER BY workplace_city")
    cities = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT workplace_state FROM jobs_all WHERE workplace_state IS NOT NULL AND workplace_state != '' ORDER BY workplace_state")
    states = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT department FROM jobs_all WHERE department IS NOT NULL AND department != '' ORDER BY department")
    departments = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT workplace_type FROM jobs_all WHERE workplace_type IS NOT NULL AND workplace_type != '' ORDER BY workplace_type")
    workplace_types = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT type FROM jobs_all WHERE type IS NOT NULL AND type != '' ORDER BY type")
    job_types = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT source FROM jobs_all WHERE source IS NOT NULL AND source != '' ORDER BY source")
    sources = [row[0] for row in cursor.fetchall()]

    return jsonify({
        'cities': cities,
        'states': states,
        'departments': departments,
        'workplace_types': workplace_types,
        'job_types': job_types,
        'sources': sources
    })


@app.route('/api/jobs/<job_id>')
def get_job(job_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT j.*, c.name as company_name, c.logo_url as company_logo, c.career_page_url as company_url
        FROM jobs_all j
        LEFT JOIN companies_all c ON j.company_id = c.id
        WHERE j.id = ?
    """, (job_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({'error': 'Job not found'}), 404

    job = dict(row)
    job['job_id'] = job['id']
    job['job_title'] = job['title']
    job['job_department'] = job['department']
    job['job_type'] = job['type']

    company = {
        'id': job['company_id'],
        'name': job['company_name'],
        'logo_url': job['company_logo'],
        'career_page_url': job['company_url']
    }
    job['job_url'] = get_job_url(job, company)
    job['company'] = company

    return jsonify(job)


if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(host=host, port=port, debug=debug)