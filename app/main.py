import logging
import os
import re
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import tqdm

from scrapers import GupyScraper, InhireScraper, LinkedInScraper, get_http_session

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def init_database_tables(db_path: str, ts: str) -> None:
    """Initialize the SQLite database with basic tables only"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS companies_{ts} (
            id TEXT PRIMARY KEY,
            name TEXT,
            logo_url TEXT,
            career_page_url TEXT,
            company_data TEXT,
            source TEXT
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS jobs_{ts} (
            id TEXT PRIMARY KEY,
            company_id TEXT,
            title TEXT,
            type TEXT,
            department TEXT,
            workplace_city TEXT,
            workplace_state TEXT,
            workplace_type TEXT,
            source TEXT
        )
    """)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        logger.error("Usage: main.py <ts> <folder> <db_file>")
        sys.exit(1)

    ts = sys.argv[1]
    folder = sys.argv[2]
    db_file = sys.argv[3]

    # Validate timestamp is numeric only (prevents SQL injection via table names)
    if not re.match(r'^[0-9]+$', ts):
        logger.error(f"timestamp must be numeric only, got: {ts}")
        sys.exit(1)

    db_path = os.path.join(folder, db_file)

    logger.debug(f"GUPY_ENABLED: {os.environ.get('GUPY_ENABLED')}")
    logger.debug(f"INHIRE_ENABLED: {os.environ.get('INHIRE_ENABLED')}")

    os.makedirs(folder, exist_ok=True)
    init_database_tables(db_path, ts)

    session = get_http_session()

    gupy_enabled = os.environ.get('GUPY_ENABLED', 'true').lower() == 'true'
    inhire_enabled = os.environ.get('INHIRE_ENABLED', 'true').lower() == 'true'
    linkedin_enabled = os.environ.get('LINKEDIN_ENABLED', 'true').lower() == 'true'

    scrapers = []
    if gupy_enabled:
        scrapers.append(GupyScraper(session))
    if inhire_enabled:
        scrapers.append(InhireScraper(session))
    if linkedin_enabled:
        scrapers.append(LinkedInScraper(session))

    if not scrapers:
        logger.warning("No scrapers enabled. Exiting.")
        sys.exit(0)

    all_companies = []
    all_jobs = []

    for scraper in scrapers:
        logger.info(f"Fetching companies from {scraper.source_name}...")
        companies = scraper.fetch_companies()
        logger.info(f"Found {len(companies)} companies in {scraper.source_name}")

        scraper_companies = 0
        scraper_jobs = 0

        with ThreadPoolExecutor(max_workers=scraper.threads) as executor:
            future_to_company = {executor.submit(scraper.fetch_jobs, company): company for company in companies}

            for future in tqdm.tqdm(as_completed(future_to_company), total=len(companies), desc=f"Scraping {scraper.source_name}"):
                try:
                    company_tuple, job_tuples = future.result()
                    all_companies.append(company_tuple)
                    all_jobs.extend(job_tuples)
                    scraper_companies += 1
                    scraper_jobs += len(job_tuples)
                except Exception as exc:
                    logger.error(f"Worker generated an exception: {exc}", exc_info=True)

        logger.info(f"Collected {scraper_jobs} jobs from {scraper_companies} companies for {scraper.source_name}")

    logger.info(f"Inserting data into database: {len(all_companies)} companies, {len(all_jobs)} jobs...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.executemany(f"INSERT OR IGNORE INTO companies_{ts} (id, name, logo_url, career_page_url, company_data, source) VALUES (?, ?, ?, ?, ?, ?)", all_companies)
        cursor.executemany(f"INSERT OR IGNORE INTO jobs_{ts} (id, company_id, title, type, department, workplace_city, workplace_state, workplace_type, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", all_jobs)
        conn.commit()
        logger.info("Database commit successful.")
    except Exception as e:
        logger.error(f"Database error: {e}", exc_info=True)
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

    logger.info(f"Total jobs scraped: {len(all_jobs)}")
