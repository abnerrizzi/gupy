#!/usr/bin/env python
import os
import sqlite3
import json
from flask import Flask, request, jsonify, g

app = Flask(__name__)

DATABASE = os.environ.get('GUPY_DATABASE', '/app/out/gupy.db')


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


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})


def get_job_url(job, company):
    source = job.get('source')
    job_id = job.get('id')
    
    if source == 'gupy':
        if company and company.get('career_page_url'):
            url = company['career_page_url']
            if '/' in url[8:]: # skip https://
                base = url[:url.find('/', 8) + 1]
                return f"{base}jobs/{job_id}"
            return f"{url.rstrip('/')}/jobs/{job_id}"
        return f"https://portal.gupy.io/job/{job_id}"
    
    if source == 'inhire':
        if company and company.get('career_page_url'):
            return f"{company['career_page_url'].rstrip('/')}/vaga/{job_id}"
        return f"https://carreira.inhire.com.br/carreiras/{job.get('company_id')}/vaga/{job_id}"
    
    return ""

@app.route('/api/jobs')
def get_jobs():
    db = get_db()
    cursor = db.cursor()

    query = """
        SELECT 
            j.*, 
            c.name as company_name, 
            c.logo_url as company_logo,
            c.career_page_url as company_url
        FROM jobs_all j
        LEFT JOIN companies_all c ON j.company_id = c.id
        WHERE 1=1
    """
    params = []

    search = request.args.get('search')
    if search:
        query += " AND j.title LIKE ?"
        params.append(f'%{search}%')

    company_id = request.args.get('company_id')
    if company_id:
        query += " AND j.company_id = ?"
        params.append(company_id)

    city = request.args.get('city')
    if city:
        query += " AND j.workplace_city = ?"
        params.append(city)

    state = request.args.get('state')
    if state:
        query += " AND j.workplace_state = ?"
        params.append(state)

    department = request.args.get('department')
    if department:
        query += " AND j.department = ?"
        params.append(department)

    workplace_type = request.args.get('workplace_type')
    if workplace_type:
        query += " AND j.workplace_type = ?"
        params.append(workplace_type)

    job_type = request.args.get('type')
    if job_type:
        query += " AND j.type = ?"
        params.append(job_type)
    
    source = request.args.get('source')
    if source:
        query += " AND j.source = ?"
        params.append(source)

    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))

    # For count, we need a simpler query or wrap the one above
    count_query = f"SELECT COUNT(*) FROM jobs_all j WHERE 1=1"
    # Re-apply filters to count_query
    count_params = []
    if search:
        count_query += " AND title LIKE ?"
        count_params.append(f'%{search}%')
    if company_id:
        count_query += " AND company_id = ?"
        count_params.append(company_id)
    if city:
        count_query += " AND workplace_city = ?"
        count_params.append(city)
    if state:
        count_query += " AND workplace_state = ?"
        count_params.append(state)
    if department:
        count_query += " AND department = ?"
        count_params.append(department)
    if workplace_type:
        count_query += " AND workplace_type = ?"
        count_params.append(workplace_type)
    if job_type:
        count_query += " AND type = ?"
        count_params.append(job_type)
    if source:
        count_query += " AND source = ?"
        count_params.append(source)

    cursor.execute(count_query, count_params)
    total = cursor.fetchone()[0]

    query += " ORDER BY j.title LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    jobs = []
    for row in rows:
        d = dict(row)
        # Compatibility with frontend expectations
        d['job_id'] = d['id']
        d['job_title'] = d['title']
        d['job_department'] = d['department']
        d['job_type'] = d['type']
        # Construct job_url
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
    debug = os.environ.get('DEBUG', 'true').lower() == 'true'
    app.run(host=host, port=port, debug=debug)
