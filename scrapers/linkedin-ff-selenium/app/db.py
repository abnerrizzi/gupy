import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

SOURCE_NAME = "linkedin"


def _slugify(name: str) -> str:
    s = (name or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s or "unknown"


def _render_sql(template: str, ts: str, linkedin_mode: str) -> str:
    # Gupy/inhire staging tables will be empty during a LinkedIn-only run, so
    # their DELETEs never fire (EXISTS guard in sqlite-init.sql) regardless of
    # mode. Use 'append' for the sibling sources to be explicit.
    return (
        template
        .replace("${ts}", ts)
        .replace("${linkedin_mode}", linkedin_mode)
        .replace("${gupy_mode}", "append")
        .replace("${inhire_mode}", "append")
    )


def _build_rows(
    jobs: List[Dict[str, Any]],
    keywords: str,
    location: str,
) -> Tuple[List[tuple], List[tuple]]:
    companies: Dict[str, tuple] = {}
    job_rows: List[tuple] = []

    for job in jobs:
        job_id = (job.get("job_id") or "").strip()
        if not job_id:
            logger.debug("Skipping job with empty job_id: title=%r", job.get("title"))
            continue

        company_name = (job.get("company") or "").strip()
        company_id = _slugify(company_name)

        if company_id not in companies:
            company_data = json.dumps(
                {"keywords": keywords, "search_location": location},
                ensure_ascii=False,
            )
            companies[company_id] = (
                company_id,
                company_name or None,
                None,
                None,
                company_data,
                SOURCE_NAME,
            )

        job_rows.append((
            job_id,
            company_id,
            job.get("title") or None,
            None,
            None,
            job.get("city") or None,
            job.get("state") or None,
            job.get("workplace_type") or None,
            SOURCE_NAME,
        ))

    return list(companies.values()), job_rows


def load_jobs_to_db(
    jobs: List[Dict[str, Any]],
    ts: str,
    db_path: str,
    sqlite_init_sql: str,
    write_mode: str = "append",
    keywords: str = "",
    location: str = "",
) -> Tuple[int, int]:
    if not re.match(r"^[0-9]+$", ts):
        raise ValueError(f"timestamp must be numeric only, got: {ts!r}")
    if write_mode not in ("replace", "append"):
        raise ValueError(f"write_mode must be 'replace' or 'append', got: {write_mode!r}")

    template = Path(sqlite_init_sql).read_text(encoding="utf-8")
    company_rows, job_rows = _build_rows(jobs, keywords, location)

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_render_sql(template, ts="0", linkedin_mode="append"))

        cursor = conn.cursor()
        cursor.executemany(
            f"INSERT OR IGNORE INTO companies_{SOURCE_NAME}_{ts} "
            "(id, name, logo_url, career_page_url, company_data, source) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            company_rows,
        )
        cursor.executemany(
            f"INSERT OR IGNORE INTO jobs_{SOURCE_NAME}_{ts} "
            "(id, company_id, title, type, department, workplace_city, "
            "workplace_state, workplace_type, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            job_rows,
        )
        conn.commit()

        conn.executescript(_render_sql(template, ts=ts, linkedin_mode=write_mode))
        conn.commit()
    finally:
        conn.close()

    logger.info(
        "Loaded %d jobs / %d companies into %s (ts=%s, mode=%s)",
        len(job_rows), len(company_rows), db_path, ts, write_mode,
    )
    return len(company_rows), len(job_rows)
