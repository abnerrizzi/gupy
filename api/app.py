#!/usr/bin/env python
import os
import sqlite3
import json
from flask import Flask, request, jsonify, g

app = Flask(__name__)

DATABASE = os.environ.get('GUPY_DATABASE', '/app/out/gupy_from_csv.db')


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


@app.route('/api/jobs')
def get_jobs():
    db = get_db()
    cursor = db.cursor()

    query = "SELECT * FROM jobs WHERE 1=1"
    params = []

    search = request.args.get('search')
    if search:
        query += " AND title LIKE ?"
        params.append(f'%{search}%')

    company_id = request.args.get('company_id')
    if company_id:
        query += " AND company_id = ?"
        params.append(company_id)

    city = request.args.get('city')
    if city:
        query += " AND workplace_city = ?"
        params.append(city)

    state = request.args.get('state')
    if state:
        query += " AND workplace_state = ?"
        params.append(state)

    department = request.args.get('department')
    if department:
        query += " AND department = ?"
        params.append(department)

    workplace_type = request.args.get('workplace_type')
    if workplace_type:
        query += " AND workplace_type = ?"
        params.append(workplace_type)

    job_type = request.args.get('type')
    if job_type:
        query += " AND type = ?"
        params.append(job_type)

    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))

    count_query = query.replace('*', 'COUNT(*)')
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    query += " ORDER BY title LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    jobs = rows_to_list(cursor.fetchall())

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
    cursor.execute("SELECT * FROM companies ORDER BY name")
    companies = rows_to_list(cursor.fetchall())
    return jsonify({'companies': companies})


@app.route('/api/filters')
def get_filters():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT DISTINCT workplace_city FROM jobs WHERE workplace_city IS NOT NULL AND workplace_city != '' ORDER BY workplace_city")
    cities = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT workplace_state FROM jobs WHERE workplace_state IS NOT NULL AND workplace_state != '' ORDER BY workplace_state")
    states = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT department FROM jobs WHERE department IS NOT NULL AND department != '' ORDER BY department")
    departments = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT workplace_type FROM jobs WHERE workplace_type IS NOT NULL AND workplace_type != '' ORDER BY workplace_type")
    workplace_types = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT type FROM jobs WHERE type IS NOT NULL AND type != '' ORDER BY type")
    job_types = [row[0] for row in cursor.fetchall()]

    return jsonify({
        'cities': cities,
        'states': states,
        'departments': departments,
        'workplace_types': workplace_types,
        'job_types': job_types
    })


@app.route('/api/jobs/<int:job_id>')
def get_job(job_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    job = row_to_dict(cursor.fetchone())

    if job:
        cursor.execute("SELECT * FROM companies WHERE id = ?", (job['company_id'],))
        company = row_to_dict(cursor.fetchone())
        job['company'] = company

    return jsonify(job)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)