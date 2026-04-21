import os
import sys
import re
import json
import sqlite3
import time
import logging
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

DEBUG = os.environ.get('DEBUG', '0') == '1'
print(f"DEBUG environment variable: {os.environ.get('DEBUG', 'NOT SET')}, DEBUG flag: {DEBUG}")

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

LINKEDIN_EMAIL = os.environ.get('LINKEDIN_EMAIL', '')
LINKEDIN_PASSWORD = os.environ.get('LINKEDIN_PASSWORD', '')
LINKEDIN_KEYWORDS = os.environ.get('LINKEDIN_KEYWORDS', 'Software Engineer')
LINKEDIN_LOCATION = os.environ.get('LINKEDIN_LOCATION', 'Brazil')
LINKEDIN_LIMIT = int(os.environ.get('LINKEDIN_LIMIT', 50))
LINKEDIN_THREADS = int(os.environ.get('LINKEDIN_THREADS', 2))
RATE_LIMIT_SLEEP = 3


class Scraper:
    def __init__(self, driver):
        self.driver = driver
        self.source_name = "unknown"
        self.limit = 50

    def fetch_companies(self):
        raise NotImplementedError

    def fetch_jobs(self, company, folder):
        raise NotImplementedError


class LinkedInFirefoxScraper(Scraper):
    def __init__(self, driver):
        super().__init__(driver)
        self.source_name = "linkedin"
        self.limit = LINKEDIN_LIMIT
        self.email = LINKEDIN_EMAIL
        self.password = LINKEDIN_PASSWORD
        self.keywords = LINKEDIN_KEYWORDS
        self.location = LINKEDIN_LOCATION

    def login(self):
        if not self.email or not self.password:
            logger.warning("LinkedIn credentials not provided, proceeding with unauthenticated access")
            return False

        try:
            logger.debug("Navigating to LinkedIn login page")
            self.driver.get("https://www.linkedin.com/login")
            logger.debug("Waiting for username field")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            self.driver.find_element(By.ID, "username").send_keys(self.email)
            self.driver.find_element(By.ID, "password").send_keys(self.password)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            time.sleep(5)
            logger.info("LinkedIn login successful")
            return True
        except Exception as e:
            logger.error(f"LinkedIn login failed: {e}")
            return False

    def fetch_companies(self):
        return [{
            'id': 'linkedin_search',
            'name': f'LinkedIn Search: {self.keywords} in {self.location}',
            'url': 'https://www.linkedin.com/jobs'
        }]

    def fetch_jobs(self, company, folder):
        job_tuples = []
        company_id = company['id']
        company_name = company['name']
        company_url = company['url']

        company_tuple = (company_id, company_name, None, company_url, json.dumps(company), self.source_name)

        keywords_enc = self.keywords.replace(' ', '%20')
        location_enc = self.location.replace(' ', '%20')
        search_url = f"https://www.linkedin.com/jobs/search/?keywords={keywords_enc}&location={location_enc}"

        def save_debug_files(prefix):
            logger.debug(f"save_debug_files called with prefix: {prefix}, DEBUG={DEBUG}")
            if DEBUG:
                try:
                    # Save to current directory first to ensure it works
                    ss_path = f"/app/out/{prefix}_screenshot.png"
                    self.driver.save_screenshot(ss_path)
                    logger.debug(f"Screenshot saved: {ss_path}")
                    src_path = f"/app/out/{prefix}_page.html"
                    with open(src_path, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    logger.debug(f"Page source saved: {src_path}")
                except Exception as e:
                    logger.debug(f"Failed to save debug files: {e}", exc_info=True)
            else:
                logger.debug(f"DEBUG is False, not saving debug files for prefix: {prefix}")

        try:
            logger.debug(f"Loading search URL: {search_url}")
            self.driver.get(search_url)
            time.sleep(3)

            start = 0
            while len(job_tuples) < self.limit:
                if start > 0:
                    scroll_url = f"{search_url}&start={start}"
                    logger.debug(f"Loading page {start // 25 + 1}: {scroll_url}")
                    self.driver.get(scroll_url)
                    time.sleep(2)

                try:
                    logger.debug("Waiting for jobs-search-results-list container")
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "jobs-search-results-list"))
                    )
                except TimeoutException:
                    logger.warning("Jobs list container not found")
                    logger.debug(f"Current URL: {self.driver.current_url}")
                    logger.debug(f"Page title: {self.driver.title}")
                    save_debug_files("jobs_list_missing")
                    break

                logger.debug("Searching for job-card-container elements")
                job_cards = self.driver.find_elements(By.CSS_SELECTOR, ".job-card-container")

                if not job_cards:
                    logger.info("No more job cards found")
                    break

                logger.debug(f"Found {len(job_cards)} job cards on page")

                for card in job_cards:
                    if len(job_tuples) >= self.limit:
                        break

                    try:
                        logger.debug("Extracting job card data")
                        title_elem = card.find_element(By.CSS_SELECTOR, ".job-card-list__title--link")
                        job_title = title_elem.text.strip()
                        job_link = title_elem.get_attribute("href")

                        job_id_match = re.search(r'/view/(\d+)', job_link)
                        job_id = job_id_match.group(1) if job_id_match else f"li_{hash(job_link)}"

                        company_elem = card.find_element(By.CSS_SELECTOR, ".job-card-container__company-name")
                        job_company_name = company_elem.text.strip()

                        location_elem = card.find_element(By.CSS_SELECTOR, ".job-card-container__metadata-item")
                        job_location = location_elem.text.strip()

                        parts = [p.strip() for p in job_location.split(',')]
                        city = parts[0] if len(parts) > 0 else "N/A"
                        state = parts[1] if len(parts) > 1 else "N/A"

                        job_tuples.append((
                            job_id,
                            company_id,
                            job_title,
                            "N/A",
                            "N/A",
                            city,
                            state,
                            "N/A",
                            self.source_name
                        ))
                        logger.info(f"Scraped: {job_title} at {job_company_name}")

                    except NoSuchElementException:
                        continue
                    except Exception as e:
                        logger.warning(f"Failed to extract job card: {e}")
                        continue

                start += 25
                time.sleep(RATE_LIMIT_SLEEP)

        except Exception as e:
            logger.error(f"Failed to fetch jobs: {e}")
            save_debug_files("fetch_jobs_error")

        return company_tuple, job_tuples


def init_database_tables(db_path, ts):
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


def create_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.set_preference("network.http.use-cache", True)

    driver = webdriver.Firefox(options=options)
    driver.set_page_load_timeout(30)
    return driver


def main(ts, folder, db_file):
    if not re.match(r'^[0-9]+$', ts):
        logger.error(f"timestamp must be numeric only, got: {ts}")
        sys.exit(1)

    os.makedirs(folder, exist_ok=True)
    db_path = os.path.join(folder, db_file)

    logger.info(f"Starting LinkedIn Firefox scraper - timestamp: {ts}")

    init_database_tables(db_path, ts)

    driver = create_driver()
    all_companies = []
    all_jobs = []

    try:
        scraper = LinkedInFirefoxScraper(driver)
        scraper.login()

        companies = scraper.fetch_companies()

        for company in companies:
            company_tuple, job_tuples = scraper.fetch_jobs(company, folder)
            all_companies.append(company_tuple)
            all_jobs.extend(job_tuples)
            time.sleep(RATE_LIMIT_SLEEP)

    except Exception as e:
        logger.error(f"Scraper error: {e}", exc_info=True)
    finally:
        driver.quit()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.executemany(f"INSERT OR IGNORE INTO companies_{ts} (id, name, logo_url, career_page_url, company_data, source) VALUES (?, ?, ?, ?, ?, ?)", all_companies)
        cursor.executemany(f"INSERT OR IGNORE INTO jobs_{ts} (id, company_id, title, type, department, workplace_city, workplace_state, workplace_type, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", all_jobs)
        conn.commit()
        logger.info(f"Database commit successful. {len(all_companies)} companies, {len(all_jobs)} jobs.")
    except Exception as e:
        logger.error(f"Database error: {e}", exc_info=True)
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        logger.error("Usage: main.py <ts> <folder> <db_file>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2], sys.argv[3])