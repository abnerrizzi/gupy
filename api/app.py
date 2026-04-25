#!/usr/bin/env python
import os
import sqlite3
import json
import logging
import time
from datetime import timedelta

from flask import Flask, request, jsonify, g, session

from fetchers import FETCHERS, FetchError
from auth import (
    current_user_id,
    hash_password,
    is_valid_password,
    is_valid_username,
    login_required,
    verify_password,
)

app = Flask(__name__)

_default_secret = 'dev-only-insecure-secret'
app.secret_key = os.environ.get('SECRET_KEY') or _default_secret
if app.secret_key == _default_secret and os.environ.get('FLASK_ENV') == 'production':
    raise RuntimeError('SECRET_KEY env var is required in production')

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = (
    os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
)
app.permanent_session_lifetime = timedelta(days=30)

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
    'jobs_gupy_detail': [('next_data', 'TEXT')],
    'jobs_inhire_detail': [('raw_payload', 'TEXT')],
    'jobs_linkedin_detail': [
        ('detail_html', 'TEXT'),
        ('job_function', 'TEXT'),
        ('industries', 'TEXT'),
        ('posted_at', 'TEXT'),
        ('num_applicants', 'INTEGER'),
    ],
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
            info = {r[1]: (r[2] or '').upper()
                    for r in con.execute(f"PRAGMA table_info({table})").fetchall()}
            if not info:
                continue
            for col, coltype in cols_required:
                want = coltype.upper()
                if col not in info:
                    logger.info('schema migration: adding %s.%s (%s)', table, col, want)
                    con.execute(f'ALTER TABLE {table} ADD COLUMN {col} {want}')
                elif info[col] != want:
                    # Earlier migration added this column with the wrong affinity
                    # (e.g. INTEGER stored as TEXT). Drop + re-add to restore the
                    # right type. SQLite keeps this a fast O(1) metadata change.
                    logger.info('schema migration: retyping %s.%s from %s to %s',
                                table, col, info[col], want)
                    con.execute(f'ALTER TABLE {table} DROP COLUMN {col}')
                    con.execute(f'ALTER TABLE {table} ADD COLUMN {col} {want}')
        con.commit()
    finally:
        con.close()


_ensure_detail_schema()


def _ensure_app_schema():
    """Create app-state tables (users, tracked_jobs) if missing. Mirrors
    sqlite-init.sql so the API works even when the file hasn't been re-applied."""
    try:
        con = sqlite3.connect(DATABASE)
    except sqlite3.OperationalError:
        return
    try:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                name TEXT,
                surname TEXT,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            )
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        existing_user_cols = {r[1] for r in con.execute("PRAGMA table_info(users)").fetchall()}
        for col in ('name', 'surname'):
            if col not in existing_user_cols:
                con.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
        con.execute("""
            CREATE TABLE IF NOT EXISTS tracked_jobs (
                user_id        INTEGER NOT NULL,
                job_id         TEXT NOT NULL,
                source         TEXT NOT NULL,
                title          TEXT NOT NULL,
                company_name   TEXT,
                company_id     TEXT,
                location       TEXT,
                job_url        TEXT,
                job_type       TEXT,
                job_department TEXT,
                workplace_type TEXT,
                workplace_city TEXT,
                workplace_state TEXT,
                stage          TEXT NOT NULL DEFAULT 'salva',
                notes          TEXT NOT NULL DEFAULT '',
                events         TEXT NOT NULL DEFAULT '[]',
                created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                updated_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                PRIMARY KEY (user_id, job_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_tracked_user ON tracked_jobs(user_id)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_tracked_user_stage ON tracked_jobs(user_id, stage)")
        con.commit()
    finally:
        con.close()


_ensure_app_schema()


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
    total_bytes = sum(len(v) if isinstance(v, (str, bytes)) else 0 for v in values)
    logger.info('[%s] upsert_detail: table=%s cols=%d total_bytes=%d fetched_at=%s',
                job_id, table, len(cols), total_bytes, fetched_at)
    t0 = time.monotonic()
    db.execute(
        f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({placeholders})",
        values,
    )
    db.commit()
    logger.info('[%s] upsert_detail: INSERT OR REPLACE committed in %.3fs',
                job_id, time.monotonic() - t0)
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


def _user_payload(row) -> dict:
    return {
        'id': row['id'],
        'username': row['username'],
        'name': row['name'] if 'name' in row.keys() else None,
        'surname': row['surname'] if 'surname' in row.keys() else None,
    }


def _login_session(user_id: int) -> None:
    session.clear()
    session['user_id'] = user_id
    session.permanent = True


def _generic_login_error():
    return jsonify({'error': 'Usuário ou senha inválidos'}), 401


@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    body = request.get_json(silent=True) or {}
    username = (body.get('username') or '').strip()
    password = body.get('password') or ''
    name = (body.get('name') or '').strip()
    surname = (body.get('surname') or '').strip()

    ok, reason = is_valid_username(username)
    if not ok:
        return jsonify({'error': reason}), 400
    ok, reason = is_valid_password(password)
    if not ok:
        return jsonify({'error': reason}), 400
    if not name or len(name) > 64:
        return jsonify({'error': 'Nome é obrigatório (até 64 caracteres)'}), 400
    if not surname or len(surname) > 64:
        return jsonify({'error': 'Sobrenome é obrigatório (até 64 caracteres)'}), 400

    db = get_db()
    try:
        cur = db.execute(
            'INSERT INTO users (username, password_hash, name, surname) VALUES (?, ?, ?, ?)',
            (username, hash_password(password), name, surname),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Esse usuário já existe'}), 409

    user_id = cur.lastrowid
    _login_session(user_id)
    return jsonify({'user': {
        'id': user_id, 'username': username, 'name': name, 'surname': surname,
    }}), 201


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    body = request.get_json(silent=True) or {}
    username = (body.get('username') or '').strip()
    password = body.get('password') or ''
    if not username or not password:
        return _generic_login_error()

    db = get_db()
    row = db.execute(
        'SELECT id, username, password_hash, name, surname FROM users WHERE username = ?',
        (username,),
    ).fetchone()
    if not row or not verify_password(password, row['password_hash']):
        return _generic_login_error()

    _login_session(row['id'])
    return jsonify({'user': _user_payload(row)})


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    session.clear()
    return ('', 204)


@app.route('/api/auth/me')
def auth_me():
    uid = current_user_id()
    if uid is None:
        return jsonify({'error': 'auth required'}), 401
    db = get_db()
    row = db.execute('SELECT id, username, name, surname FROM users WHERE id = ?', (uid,)).fetchone()
    if not row:
        session.clear()
        return jsonify({'error': 'auth required'}), 401
    return jsonify({'user': _user_payload(row)})


# ── Tracker (saved jobs) ──────────────────────────────────────────────────

STAGE_ORDER = ['salva', 'aplicada', 'entrev', 'prop', 'encer']
STAGE_LABELS = {
    'salva': 'Salva',
    'aplicada': 'Aplicada',
    'entrev': 'Entrevista',
    'prop': 'Proposta',
    'encer': 'Encerrada',
}

_TRACKER_FIELDS = (
    'job_id', 'source', 'title', 'company_name', 'company_id', 'location',
    'job_url', 'job_type', 'job_department', 'workplace_type',
    'workplace_city', 'workplace_state', 'stage', 'notes', 'events',
    'created_at', 'updated_at',
)


def _tracker_row_to_dict(row) -> dict:
    out = {k: row[k] for k in _TRACKER_FIELDS}
    try:
        out['events'] = json.loads(out['events']) if out['events'] else []
    except (TypeError, ValueError):
        out['events'] = []
    return out


def _today_label() -> str:
    from datetime import datetime
    months = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
    now = datetime.now()
    return f'{now.day:02d} {months[now.month - 1]}'


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


@app.route('/api/me/tracked', methods=['GET'])
@login_required
def tracker_list():
    db = get_db()
    rows = db.execute(
        f"SELECT {','.join(_TRACKER_FIELDS)} FROM tracked_jobs WHERE user_id = ? ORDER BY created_at",
        (current_user_id(),),
    ).fetchall()
    return jsonify({'tracked': [_tracker_row_to_dict(r) for r in rows]})


@app.route('/api/me/tracked', methods=['POST'])
@login_required
def tracker_add():
    body = request.get_json(silent=True) or {}
    job_id = (body.get('job_id') or body.get('id') or '').strip()
    source = (body.get('source') or '').strip()
    title = (body.get('title') or '').strip()
    if not job_id or not source or not title:
        return jsonify({'error': 'job_id, source e title são obrigatórios'}), 400

    user_id = current_user_id()
    db = get_db()
    existing = db.execute(
        f"SELECT {','.join(_TRACKER_FIELDS)} FROM tracked_jobs WHERE user_id = ? AND job_id = ?",
        (user_id, job_id),
    ).fetchone()
    if existing:
        return jsonify({'tracked': _tracker_row_to_dict(existing)})

    events = json.dumps([{'when': _today_label(), 'what': 'Vaga salva'}])
    now = _now_iso()
    db.execute(
        """INSERT INTO tracked_jobs
           (user_id, job_id, source, title, company_name, company_id, location,
            job_url, job_type, job_department, workplace_type,
            workplace_city, workplace_state, stage, notes, events, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'salva', '', ?, ?, ?)""",
        (
            user_id, job_id, source, title,
            body.get('company_name'), body.get('company_id'), body.get('location'),
            body.get('job_url'), body.get('job_type'), body.get('job_department'),
            body.get('workplace_type'), body.get('workplace_city'), body.get('workplace_state'),
            events, now, now,
        ),
    )
    db.commit()
    row = db.execute(
        f"SELECT {','.join(_TRACKER_FIELDS)} FROM tracked_jobs WHERE user_id = ? AND job_id = ?",
        (user_id, job_id),
    ).fetchone()
    return jsonify({'tracked': _tracker_row_to_dict(row)}), 201


@app.route('/api/me/tracked/<job_id>', methods=['PATCH'])
@login_required
def tracker_update(job_id):
    body = request.get_json(silent=True) or {}
    user_id = current_user_id()
    db = get_db()
    row = db.execute(
        f"SELECT {','.join(_TRACKER_FIELDS)} FROM tracked_jobs WHERE user_id = ? AND job_id = ?",
        (user_id, job_id),
    ).fetchone()
    if not row:
        return jsonify({'error': 'not found'}), 404

    sets = []
    params = []
    new_stage = body.get('stage')
    new_notes = body.get('notes')

    if new_stage is not None:
        if new_stage not in STAGE_ORDER:
            return jsonify({'error': f'stage inválido (use um de {STAGE_ORDER})'}), 400
        if new_stage != row['stage']:
            try:
                events = json.loads(row['events']) if row['events'] else []
            except (TypeError, ValueError):
                events = []
            events.append({'when': _today_label(), 'what': f'Movida para {STAGE_LABELS[new_stage]}'})
            sets.append('stage = ?')
            params.append(new_stage)
            sets.append('events = ?')
            params.append(json.dumps(events))

    if new_notes is not None:
        sets.append('notes = ?')
        params.append(str(new_notes))

    if not sets:
        return jsonify({'tracked': _tracker_row_to_dict(row)})

    sets.append('updated_at = ?')
    params.append(_now_iso())
    params.extend([user_id, job_id])
    db.execute(
        f"UPDATE tracked_jobs SET {', '.join(sets)} WHERE user_id = ? AND job_id = ?",
        params,
    )
    db.commit()
    row = db.execute(
        f"SELECT {','.join(_TRACKER_FIELDS)} FROM tracked_jobs WHERE user_id = ? AND job_id = ?",
        (user_id, job_id),
    ).fetchone()
    return jsonify({'tracked': _tracker_row_to_dict(row)})


@app.route('/api/me/tracked/<job_id>', methods=['DELETE'])
@login_required
def tracker_remove(job_id):
    user_id = current_user_id()
    db = get_db()
    cur = db.execute(
        'DELETE FROM tracked_jobs WHERE user_id = ? AND job_id = ?',
        (user_id, job_id),
    )
    db.commit()
    if cur.rowcount == 0:
        return jsonify({'error': 'not found'}), 404
    return ('', 204)


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

    # Filtered count drives pagination; grand_total powers the "X of Y"
    # header indicator so the SPA can show how much is hidden by filters.
    count_query = f"SELECT COUNT(*) FROM jobs_all j WHERE 1=1 {where_str}"
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM jobs_all')
    grand_total = cursor.fetchone()[0]

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
        'grand_total': grand_total,
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
    req_start = time.monotonic()
    logger.info('[%s] ==> POST /api/jobs/%s/detail/fetch (remote=%s ua=%r)',
                job_id, job_id, request.remote_addr,
                request.headers.get('User-Agent', '-'))
    db = get_db()
    cursor = db.cursor()

    logger.info('[%s] phase 1: resolving job context from jobs_all', job_id)
    ctx = _lookup_job_context(cursor, job_id)
    if not ctx:
        logger.warning('[%s] <== 404 job not found in jobs_all', job_id)
        return jsonify({'error': 'Job not found'}), 404
    source = ctx['source']
    logger.info('[%s] phase 1: resolved source=%s company_id=%s career_page_url=%s title=%r',
                job_id, source, ctx.get('company_id'),
                ctx.get('career_page_url'), ctx.get('title'))

    fetcher = FETCHERS.get(source)
    if not fetcher:
        logger.warning('[%s] <== 400 no fetcher for source=%r', job_id, source)
        return jsonify({'error': f'Unknown source: {source}'}), 400

    logger.info('[%s] phase 2: dispatching to fetcher=%s.%s',
                job_id, fetcher.__module__, fetcher.__name__)
    t_fetch = time.monotonic()
    try:
        fields = fetcher(job_id=job_id, context=ctx)
    except NotImplementedError as exc:
        logger.warning('[%s] <== 501 fetcher not implemented: %s', job_id, exc)
        return jsonify({'error': str(exc), 'source': source}), 501
    except FetchError as exc:
        logger.error('[%s] <== 502 FetchError after %.2fs: %s',
                     job_id, time.monotonic() - t_fetch, exc, exc_info=True)
        return jsonify({'error': str(exc), 'source': source}), 502
    logger.info('[%s] phase 2: fetcher returned %d fields in %.2fs — sizes: %s',
                job_id, len(fields), time.monotonic() - t_fetch,
                {k: (len(v) if isinstance(v, (str, bytes)) else v) for k, v in fields.items()})

    logger.info('[%s] phase 3: upserting into %s', job_id, DETAIL_TABLES[source])
    detail = upsert_detail(db, source, job_id, fields)

    elapsed = time.monotonic() - req_start
    logger.info('[%s] <== 200 POST complete in %.2fs', job_id, elapsed)
    return jsonify(detail)


@app.route('/api/jobs/<job_id>/detail')
def get_job_detail(job_id):
    req_start = time.monotonic()
    logger.info('[%s] ==> GET /api/jobs/%s/detail', job_id, job_id)
    db = get_db()
    cursor = db.cursor()
    source = _lookup_source(cursor, job_id)
    if not source:
        logger.info('[%s] <== 404 job not found (%.3fs)', job_id, time.monotonic() - req_start)
        return jsonify({'error': 'Job not found'}), 404
    table = DETAIL_TABLES.get(source)
    if not table:
        logger.warning('[%s] <== 400 unknown source=%r', job_id, source)
        return jsonify({'error': f'Unknown source: {source}'}), 400
    cursor.execute(f"SELECT * FROM {table} WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    if not row:
        logger.info('[%s] <== 404 %s.%s not fetched yet (%.3fs)',
                    job_id, table, job_id, time.monotonic() - req_start)
        return jsonify({'error': 'Detail not fetched yet', 'source': source}), 404
    detail = dict(row)
    detail['source'] = source
    sizes = {k: len(v) for k, v in detail.items() if isinstance(v, str)}
    logger.info('[%s] <== 200 %s row returned in %.3fs — sizes: %s',
                job_id, table, time.monotonic() - req_start, sizes)
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
