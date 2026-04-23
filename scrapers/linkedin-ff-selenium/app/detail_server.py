"""On-demand LinkedIn detail fetcher.

A Flask app that keeps a Selenium driver warm and services `POST /fetch/<id>`
requests from the main API. Runs under the `linkedin` compose profile so it
doesn't autostart on bare `docker compose up`."""
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone

from flask import Flask, jsonify

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


def _get_scraper() -> LinkedInSeleniumScraper:
    global _scraper
    if _scraper is None:
        logger.info('Bootstrapping Selenium session at %s', config.SELENIUM_URL)
        session = BrowserSession(config.SELENIUM_URL, config.BROWSER_TIMEOUT)
        session.create_driver()
        _scraper = LinkedInSeleniumScraper(session)
    return _scraper


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/fetch/<job_id>', methods=['POST'])
def fetch_detail(job_id: str):
    job_url = f'https://www.linkedin.com/jobs/view/{job_id}'
    with _driver_lock:
        try:
            scraper = _get_scraper()
            result = scraper.scrape_detail_page(job_url)
        except Exception as exc:
            logger.error('scrape_detail_page failed for %s: %s', job_id, exc, exc_info=True)
            return jsonify({'error': f'scrape failed: {exc}'}), 502

    if not result or not result.get('description'):
        return jsonify({'error': 'detail page returned no description'}), 502

    fetched_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
    with sqlite3.connect(config.DB_PATH) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute(
            'INSERT OR REPLACE INTO jobs_linkedin_detail '
            '(id, description, seniority, employment_type, fetched_at) '
            'VALUES (?, ?, ?, ?, ?)',
            (
                job_id,
                result.get('description', ''),
                result.get('seniority', ''),
                result.get('employment_type', ''),
                fetched_at,
            ),
        )
        db.commit()

    return jsonify({
        'id': job_id,
        'description': result.get('description', ''),
        'seniority': result.get('seniority', ''),
        'employment_type': result.get('employment_type', ''),
        'fetched_at': fetched_at,
        'source': 'linkedin',
    })


if __name__ == '__main__':
    host = os.environ.get('DETAIL_SERVER_HOST', '0.0.0.0')
    port = int(os.environ.get('DETAIL_SERVER_PORT', '8000'))
    logger.info('LinkedIn detail server listening on %s:%d', host, port)
    app.run(host=host, port=port, debug=False, use_reloader=False)
