import os
import sys
import json
import sqlite3
import time
import logging
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.firefox import GeckoDriverManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

LINKEDIN_EMAIL = os.environ.get('LINKEDIN_EMAIL', '')
LINKEDIN_PASSWORD = os.environ.get('LINKEDIN_PASSWORD', '')
LINKEDIN_KEYWORDS = os.environ.get('LINKEDIN_KEYWORDS', 'Software Engineer')
LINKEDIN_LOCATION = os.environ.get('LINKEDIN_LOCATION', 'Brazil')
LINKEDIN_LIMIT = int(os.environ.get('LINKEDIN_LIMIT', 50))
RATE_LIMIT_SLEEP = 3

class Scraper:
    def __init__(self, driver):
        self.driver = driver
        self.source_name = "unknown"
        self.limit = 50

    def fetch_companies(self):
        raise NotImplementedError

    def fetch_jobs(self, company):
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
            self.driver.get("https://www.linkedin.com/login")
            WebDriverWait(self.driver, 10).until(
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
        return [{"id": "linkedin_search", "name": f"LinkedIn: {self.keywords} in {self.location}", "url": "https://www.linkedin.com/jobs"}]

    def fetch_jobs(self, company):
        job_tuples = []
        company_id = company["id"]
        company_name = company["name"]
        company_url = company["url"]
        company_tuple = (company_id, company_name, None, company_url, json.dumps(company), self.source_name)

        search_url = f"https://www.linkedin.com/jobs/search/?keywords={self.keywords.replace(' ', '%20')}&location={self.location.replace(' ', '%20')}"
        
        try:
            self.driver.get(search_url)
            time.sleep(3)
            
            jobs_container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "jobs-search-results-list"))
            )
            
            job_cards = self.driver.find_elements(By.CLASS_NAME, "job-card-container")
            
            for idx, job_card in enumerate(job_cards[:self.limit]):
                try:
                    title_elem = job_card.find_element(By.CLASS_NAME, "job-card-list__title")
                    job_title = title_elem.text.strip()
                    job_url = title_elem.get_attribute("href")
                    
                    company_elem = job_card.find_element(By.CLASS_NAME, "job-card-container__company-name")
                    job_company = company_elem.text.strip()
                    
                    location_elem = job_card.find_element(By.CLASS_NAME, "job-card-container__metadata-item")
                    job_location = location_elem.text.strip()
                    
                    job_id = f"linkedin_{idx}"
                    job_tuples.append((job_id, company_id, job_title, job_company, job_location, "N/A", "N/A", self.source_name))
                    logger.info(f"Scraped job: {job_title} at {job_company}")
                    
                except Exception as e:
                    logger.warning(f"Failed to extract job card: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to fetch jobs: {e}")
            
        return company_tuple, job_tuples


def init_database(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id TEXT PRIMARY KEY,
            name TEXT,
            domain TEXT,
            career_page_url TEXT,
            data TEXT,
            source TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT,
            company_id TEXT,
            title TEXT,
            company_name TEXT,
            location TEXT,
            description TEXT,
            source TEXT,
            PRIMARY KEY (id, source)
        )
    """)
    conn.commit()
    conn.close()


def save_to_db(db_path: str, companies: list, jobs: list) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for company in companies:
        cursor.execute("""
            INSERT OR REPLACE INTO companies (id, name, domain, career_page_url, data, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, company)
    
    for job in jobs:
        cursor.execute("""
            INSERT OR REPLACE INTO jobs (id, company_id, title, company_name, location, description, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, job)
    
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


def main(ts: str, folder: str, db_file: str):
    os.makedirs(folder, exist_ok=True)
    db_path = os.path.join(folder, db_file)
    
    logger.info(f"Starting LinkedIn Firefox scraper - timestamp: {ts}")
    
    init_database(db_path)
    
    driver = create_driver()
    all_companies = []
    all_jobs = []
    
    try:
        scraper = LinkedInFirefoxScraper(driver)
        scraper.login()
        
        companies = scraper.fetch_companies()
        
        for company in companies:
            company_tuple, job_tuples = scraper.fetch_jobs(company)
            all_companies.append(company_tuple)
            all_jobs.extend(job_tuples)
            time.sleep(RATE_LIMIT_SLEEP)
            
    except Exception as e:
        logger.error(f"Scraper error: {e}", exc_info=True)
    finally:
        driver.quit()
    
    save_to_db(db_path, all_companies, all_jobs)
    logger.info(f"Saved {len(all_companies)} companies and {len(all_jobs)} jobs to {db_path}")


if __name__ == "__main__":
    ts = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d%H%M%S")
    folder = sys.argv[2] if len(sys.argv) > 2 else "out"
    db_file = sys.argv[3] if len(sys.argv) > 3 else "jobhubmine.db"
    main(ts, folder, db_file)
