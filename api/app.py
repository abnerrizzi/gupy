#!/usr/bin/env python
import os
import sqlite3
import json
import logging
from flask import Flask, request, jsonify, g

from fetchers import FETCHERS, FetchError

app = Flask(__name__)

logging.basicConfig(
    level=os.environ.get('LOG_LEVEL', 'INFO'),
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

DATABASE = os.environ.get('JOBHUBMINE_DATABASE', '/app/out/jobhubmine.db')

DETAIL_TABLES = {
    'gupy': 'jobs_gupy_detail',
    'inhire': 'jobs_inhire_detail',
    'linkedin': 'jobs_linkedin_detail',
}


def _enable_wal(db):
    # Enable WAL once per DB file so the API and a concurrent scraper run
    # don't block each other. Idempotent — safe on every open.
    db.execute('PRAGMA journal_mode=WAL')


_DETAIL_MIGRATIONS = {
    'jobs_gupy_detail': ['next_data'],
    'jobs_inhire_detail': ['raw_payload'],
    'jobs_linkedin_detail': ['detail_html'],
}


def _ensure_detail_schema():
    """Idempotent per-worker migration: add detail columns that were
    introduced after the table first landed. CREATE TABLE IF NOT EXISTS
    can't alter existing tables, so we check PRAGMA + ALTER when missing."""
    try:
        con = sqlite3.connect(DATABASE)
    except sqlite3.OperationalError:
        return
    try:
        for table, cols_required in _DETAIL_MIGRATIONS.items():
            existing = {r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}
            if not existing:
                continue
            for col in cols_required:
                if col not in existing:
                    logger.info('schema migration: adding %s.%s', table, col)
                    con.execute(f'ALTER TABLE {table} ADD COLUMN {col} TEXT')
        con.commit()
    finally:
        con.close()


_ensure_detail_schema()


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        _enable_wal(db)
    return db


def upsert_detail(db, source: str, job_id: str, fields: dict) -> dict:
    """Insert-or-replace a detail row. `fields` keys must match the columns of
    the target table (minus `id` and `fetched_at`, which are set here).
    Returns the persisted row as a dict (source-agnostic caller contract)."""
    table = DETAIL_TABLES[source]
    from datetime import datetime, timezone
    fetched_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
    cols = ['id'] + list(fields.keys()) + ['fetched_at']
    placeholders = ','.join(['?'] * len(cols))
    values = [job_id] + list(fields.values()) + [fetched_at]
    db.execute(
        f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({placeholders})",
        values,
    )
    db.commit()
    cursor = db.cursor()
    cursor.execute(f"SELECT * FROM {table} WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    result = dict(row)
    result['source'] = source
    return result


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
    """Build WHERE clause and params from request arguments"""
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
        'workplace_type_label': (None, None), # Handled separately
        'job_type_label': (None, None) # Handled separately
    }

    for arg_name, (clause, transform) in filters.items():
        if clause is None: continue
        value = args.get(arg_name)
        if value:
            where_clauses.append(clause)
            params.append(transform(value) if transform else value)

    # Handle grouped labels for workplace_type
    wp_label = args.get('workplaceType') # Frontend sends 'workplaceType'
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

    # Handle grouped labels for job_type
    jt_label = args.get('jobType') # Frontend sends 'jobType'
    if jt_label:
        if jt_label == 'Efetiva':
            where_clauses.append("LOWER(j.type) IN ('vacancy_type_effective', 'efetivo', 'full-time')")
        elif jt_label == 'Banco de Talentos':
            where_clauses.append("LOWER(j.type) IN ('vacancy_type_talent_pool', 'banco de talentos')")
        elif jt_label == 'Estágio':
            where_clauses.append("LOWER(j.type) IN ('vacancy_type_internship', 'estágio', 'internship')")
        elif jt_label == 'Jovem Aprendiz':
            where_clauses.append("LOWER(j.type) IN ('vacancy_type_apprentice', 'aprendiz')")
        elif jt_label == 'Temporário':
            where_clauses.append("LOWER(j.type) IN ('vacancy_type_temporary', 'temporário')")
        elif jt_label == 'Docente':
            where_clauses.append("LOWER(j.type) IN ('vacancy_type_lecturer', 'palestrante', 'docente')")
        elif jt_label == 'PJ':
            where_clauses.append("LOWER(j.type) IN ('vacancy_legal_entity', 'pj')")
        elif jt_label == 'Associado':
            where_clauses.append("LOWER(j.type) IN ('vacancy_type_associate', 'associado')")
        elif jt_label == 'Autônomo':
            where_clauses.append("LOWER(j.type) IN ('vacancy_type_autonomous', 'autônomo')")
        elif jt_label == 'Outros':
            where_clauses.append("(j.type IS NULL OR j.type = '' OR j.type = 'N/A')")
        else:
            where_clauses.append("j.type = ?")
            params.append(jt_label)

    where_str = ""
    if where_clauses:
        where_str = " AND " + " AND ".join(where_clauses)

    # Build ORDER BY clause
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
    """Safely cast value to int with bounds"""
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
    
    if source == 'gupy':
        if company and company.get('career_page_url'):
            url = company['career_page_url']
            if '/' in url[8:]: # skip https://
                base = url[:url.find('/', 8) + 1]
                return f"{base}jobs/{job_id}"
            return f"{url.rstrip('/')}/jobs/{job_id}"
        return f"https://portal.gupy.io/job/{job_id}"
    
    if source == 'inhire':
        tenant = job.get('company_id')
        return f"https://{tenant}.inhire.app/vagas/{job_id}/description"

    if source == 'linkedin':
        return f"https://www.linkedin.com/jobs/view/{job_id}"

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

    # For count, we reuse the same filter logic but must adjust column names if necessary
    # (In this case jobs_all has all columns, so j. prefix from build_filters is fine if we alias)
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


def _lookup_source(cursor, job_id):
    cursor.execute("SELECT source FROM jobs_all WHERE id = ? LIMIT 1", (job_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def _lookup_job_context(cursor, job_id):
    cursor.execute(
        """
        SELECT j.source, j.company_id, j.title, c.name AS company_name,
               c.career_page_url
        FROM jobs_all j
        LEFT JOIN companies_all c ON j.company_id = c.id
        WHERE j.id = ?
        LIMIT 1
        """,
        (job_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


@app.route('/api/jobs/<job_id>/detail/fetch', methods=['POST'])
def fetch_job_detail(job_id):
    db = get_db()
    cursor = db.cursor()
    ctx = _lookup_job_context(cursor, job_id)
    if not ctx:
        return jsonify({'error': 'Job not found'}), 404
    source = ctx['source']
    fetcher = FETCHERS.get(source)
    if not fetcher:
        return jsonify({'error': f'Unknown source: {source}'}), 400
    try:
        fields = fetcher(job_id=job_id, context=ctx)
    except NotImplementedError as exc:
        return jsonify({'error': str(exc), 'source': source}), 501
    except FetchError as exc:
        logger.error("detail fetch failed for %s/%s: %s", source, job_id, exc,
                     exc_info=True)
        return jsonify({'error': str(exc), 'source': source}), 502
    detail = upsert_detail(db, source, job_id, fields)
    return jsonify(detail)


@app.route('/api/jobs/<job_id>/detail')
def get_job_detail(job_id):
    db = get_db()
    cursor = db.cursor()
    source = _lookup_source(cursor, job_id)
    if not source:
        return jsonify({'error': 'Job not found'}), 404
    table = DETAIL_TABLES.get(source)
    if not table:
        return jsonify({'error': f'Unknown source: {source}'}), 400
    cursor.execute(f"SELECT * FROM {table} WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({'error': 'Detail not fetched yet', 'source': source}), 404
    detail = dict(row)
    detail['source'] = source
    return jsonify(detail)


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
