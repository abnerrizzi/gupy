"""On-demand LinkedIn detail fetcher.

A Flask app that keeps a Selenium driver warm and services `POST /fetch/<id>`
requests from the main API. Runs under the `linkedin` compose profile so it
doesn't autostart on bare `docker compose up`."""
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone

from flask import Flask, jsonify
from selenium.common.exceptions import WebDriverException

from app import config
from app.browser import BrowserSession
from app.linkedin import LinkedInSeleniumScraper

logging.basicConfig(
    level=os.environ.get('LOG_LEVEL_STDOUT', 'INFO'),
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

_driver_lock = threading.Lock()
_scraper: LinkedInSeleniumScraper | None = None


def _ensure_schema() -> None:
    """Idempotent schema migration: add columns introduced after the initial
    jobs_linkedin_detail table landed. CREATE TABLE IF NOT EXISTS can't alter
    existing tables, so we check PRAGMA table_info and ALTER when missing."""
    with sqlite3.connect(config.DB_PATH) as db:
        cur = db.execute("PRAGMA table_info(jobs_linkedin_detail)")
        cols = {row[1] for row in cur.fetchall()}
        if cols and 'detail_html' not in cols:
            logger.info('schema migration: adding jobs_linkedin_detail.detail_html')
            db.execute('ALTER TABLE jobs_linkedin_detail ADD COLUMN detail_html TEXT')
            db.commit()


def _create_scraper() -> LinkedInSeleniumScraper:
    logger.info('Bootstrapping Selenium session at %s', config.SELENIUM_URL)
    t0 = time.monotonic()
    session = BrowserSession(config.SELENIUM_URL, config.BROWSER_TIMEOUT)
    driver = session.create_driver()
    logger.info('Selenium driver ready in %.1fs — session_id=%s',
                time.monotonic() - t0, driver.session_id)
    return LinkedInSeleniumScraper(session)


def _get_scraper() -> LinkedInSeleniumScraper:
    global _scraper
    if _scraper is None:
        _scraper = _create_scraper()
    return _scraper


def _reset_scraper() -> None:
    """Drop the cached driver after a session-lost error. Selenium nodes GC
    idle sessions (~3 min of inactivity) so the cached driver goes stale
    between requests — detect + recreate on the next fetch."""
    global _scraper
    if _scraper is not None:
        try:
            _scraper.driver.quit()
        except WebDriverException:
            pass
    _scraper = None


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


def _capture_detail_html(driver) -> str:
    """Grab the rendered HTML of the main job-detail content region. Falls
    back to the full page source if <main> is not present."""
    try:
        el = driver.find_element('css selector', 'main')
        html = el.get_attribute('outerHTML') or ''
        if html:
            return html
    except WebDriverException:
        pass
    return driver.page_source or ''


def _scrape_with_retry(job_id: str, job_url: str) -> dict:
    """Navigate + parse + capture page HTML, with one recovery attempt if
    the cached Selenium session died between requests. Emits step-level logs
    so the operator can follow along in `docker compose logs linkedin-detail`."""
    scraper = _get_scraper()

    def _attempt(label: str) -> dict:
        logger.info('[%s] step 1: parse via LinkedInSeleniumScraper.scrape_detail_page '
                    '(%s, session_id=%s)',
                    job_id, label, getattr(scraper.driver, 'session_id', '?'))
        t0 = time.monotonic()
        parsed = scraper.scrape_detail_page(job_url)
        try:
            current_url = scraper.driver.current_url
            page_title = scraper.driver.title
        except WebDriverException:
            current_url = page_title = '<unreachable>'
        logger.info('[%s] step 2: parse returned desc_len=%d seniority=%r '
                    'employment_type=%r (%.1fs) — title=%r current_url=%r',
                    job_id,
                    len(parsed.get('description', '') or ''),
                    parsed.get('seniority'),
                    parsed.get('employment_type'),
                    time.monotonic() - t0,
                    page_title,
                    current_url)
        if parsed.get('description'):
            logger.info('[%s] step 3: capturing rendered detail html', job_id)
            t1 = time.monotonic()
            parsed['detail_html'] = _capture_detail_html(scraper.driver)
            logger.info('[%s] step 3: detail_html captured bytes=%d (%.1fs)',
                        job_id, len(parsed['detail_html']), time.monotonic() - t1)
        return parsed

    logger.info('[%s] navigating to %s', job_id, job_url)
    try:
        result = _attempt('try #1')
    except WebDriverException as exc:
        logger.warning('[%s] driver error during try #1 — rebuilding: %s', job_id, exc)
        _reset_scraper()
        scraper = _get_scraper()
        result = _attempt('try #2 (after rebuild)')

    if result and result.get('description'):
        return result

    # scrape_detail_page swallows WebDriverException internally and returns
    # {}. Probe driver.title to decide whether an empty result means a dead
    # session (→ rebuild + retry) or a real auth-wall / rate-limit.
    logger.info('[%s] empty result — probing driver to distinguish dead session vs auth-wall',
                job_id)
    try:
        title = scraper.driver.title
        logger.info('[%s] driver.title=%r → session alive; treating as upstream block',
                    job_id, title)
    except WebDriverException:
        logger.warning('[%s] driver.title raised → session dead; rebuilding + retrying', job_id)
        _reset_scraper()
        scraper = _get_scraper()
        result = _attempt('try #2 (after session-dead rebuild)')

    return result or {}


@app.route('/fetch/<job_id>', methods=['POST'])
def fetch_detail(job_id: str):
    job_url = f'https://www.linkedin.com/jobs/view/{job_id}'
    t_start = time.monotonic()
    logger.info('[%s] ==> fetch start', job_id)
    with _driver_lock:
        try:
            result = _scrape_with_retry(job_id, job_url)
        except Exception as exc:
            logger.error('[%s] scrape failed: %s', job_id, exc, exc_info=True)
            return jsonify({'error': f'scrape failed: {exc}'}), 502

    if not result or not result.get('description'):
        logger.warning('[%s] <== fetch giving up after %.1fs — no description returned',
                       job_id, time.monotonic() - t_start)
        return jsonify({'error': 'detail page returned no description'}), 502

    fetched_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
    logger.info('[%s] step 4: upserting into jobs_linkedin_detail', job_id)
    with sqlite3.connect(config.DB_PATH) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute(
            'INSERT OR REPLACE INTO jobs_linkedin_detail '
            '(id, description, seniority, employment_type, detail_html, fetched_at) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (
                job_id,
                result.get('description', ''),
                result.get('seniority', ''),
                result.get('employment_type', ''),
                result.get('detail_html', ''),
                fetched_at,
            ),
        )
        db.commit()

    total = time.monotonic() - t_start
    logger.info('[%s] <== fetch done in %.1fs (desc=%d detail_html=%d)',
                job_id, total,
                len(result.get('description', '') or ''),
                len(result.get('detail_html', '') or ''))

    return jsonify({
        'id': job_id,
        'description': result.get('description', ''),
        'seniority': result.get('seniority', ''),
        'employment_type': result.get('employment_type', ''),
        'detail_html': result.get('detail_html', ''),
        'fetched_at': fetched_at,
        'source': 'linkedin',
    })


if __name__ == '__main__':
    _ensure_schema()
    host = os.environ.get('DETAIL_SERVER_HOST', '0.0.0.0')
    port = int(os.environ.get('DETAIL_SERVER_PORT', '8000'))
    logger.info('LinkedIn detail server listening on %s:%d', host, port)
    app.run(host=host, port=port, debug=False, use_reloader=False)
