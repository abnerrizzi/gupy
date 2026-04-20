import os
import sys
import re
import requests
import json
import sqlite3
import tqdm
import time
import logging
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Constants
GUPY_LIMIT = int(os.environ.get('GUPY_COMPANY_LIMIT', 30))
INHIRE_LIMIT = int(os.environ.get('INHIRE_COMPANY_LIMIT', 10))
GUPY_THREADS = int(os.environ.get('GUPY_THREADS', 16))
INHIRE_THREADS = int(os.environ.get('INHIRE_THREADS', 16))
LINKEDIN_THREADS = int(os.environ.get('LINKEDIN_THREADS', 2))
LINKEDIN_LIMIT = int(os.environ.get('LINKEDIN_COMPANY_LIMIT', 100)) # Number of jobs to fetch
LINKEDIN_KEYWORDS = os.environ.get('LINKEDIN_KEYWORDS', 'Software Engineer')
LINKEDIN_LOCATION = os.environ.get('LINKEDIN_LOCATION', 'Brazil')
GUPY_TIMEOUT = 30
INHIRE_TIMEOUT = 15
LINKEDIN_TIMEOUT = 30
RATE_LIMIT_SLEEP = 2

class Scraper:
    def __init__(self, session):
        self.session = session
        self.source_name = "unknown"
        self.limit = 30
        self.threads = 1

    def fetch_companies(self):
        raise NotImplementedError

    def fetch_jobs(self, company):
        raise NotImplementedError

class GupyScraper(Scraper):
    def __init__(self, session):
        super().__init__(session)
        self.source_name = "gupy"
        self.limit = GUPY_LIMIT
        self.threads = GUPY_THREADS

    def fetch_companies(self):
        # We use a separate limit for Gupy if needed, but here we respect self.limit
        url = f'https://portal.api.gupy.io/api/company?limit={self.limit}'
        try:
            response = self.session.get(url, timeout=GUPY_TIMEOUT)
            response.raise_for_status()
            return response.json().get('data', [])
        except Exception as e:
            logger.error(f"Failed to fetch Gupy company list: {e}")
            return []

    def fetch_jobs(self, company):
        company_id = company['companyId']
        company_name = company['careerPageName']
        company_career_page_url = company['careerPageUrl']
        company_data = json.dumps(company)
        
        company_tuple = (company_id, company_name, None, company_career_page_url, company_data, self.source_name)
        job_tuples = []
        
        if company_career_page_url:
            try:
                job_response = self.session.get(company_career_page_url, timeout=GUPY_TIMEOUT)
                job_response.raise_for_status()
                soup = BeautifulSoup(job_response.content, 'html.parser')
                script_tag = soup.find('script', {'id': '__NEXT_DATA__'})            
                if script_tag:
                    script_content = script_tag.contents[0]
                    script_json = json.loads(script_content)
                    
                    job_data = script_json.get('props', {}).get('pageProps', {}).get('jobs', [])
                    for job in job_data:
                        job_id = job.get('id', '')
                        job_title = job.get('title', 'N/A')
                        job_type = job.get('type', 'N/A')
                        department = job.get('department', 'N/A')                    
                        workplace = job.get('workplace', {}).get('address', {})
                        workplace_city = workplace.get('city', 'N/A')
                        workplace_state = workplace.get('state', 'N/A')
                        workplace_type = job.get('workplace', {}).get('workplaceType', 'N/A')
                        
                        job_tuples.append((job_id, company_id, job_title, job_type, department, workplace_city, workplace_state, workplace_type, self.source_name))
            
            except Exception as e:
                logger.error(f"Error processing Gupy jobs for company {company_id}: {e}")
        
        return company_tuple, job_tuples

class InhireScraper(Scraper):
    def __init__(self, session):
        super().__init__(session)
        self.source_name = "inhire"
        self.limit = INHIRE_LIMIT
        self.threads = INHIRE_THREADS

    def fetch_companies(self):
        url = "https://carreira.inhire.com.br/carreiras/"
        try:
            response = self.session.get(url, timeout=INHIRE_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            links = soup.select('li.page_item a')
            companies = []
            for link in links:
                href = link.get('href', '')
                if 'carreira.inhire.com.br/carreiras/' in href and href != url:
                    # Title is company name
                    title = link.text.replace('Carreiras | ', '').strip()
                    tenant = href.strip('/').split('/')[-1]
                    
                    companies.append({
                        'tenant': tenant,
                        'name': title,
                        'url': href
                    })
            companies.insert(0, {'tenant': 'yandeh', 'name': 'Yandeh', 'url': 'https://carreira.inhire.com.br/carreiras/yandeh/'})
            # For Inhire, we fetch based on INHIRE_LIMIT
            limited_companies = companies[:self.limit]
            logger.debug(f"Limited to {len(limited_companies)} companies")
            return limited_companies
        except Exception as e:
            logger.error(f"Failed to fetch Inhire company list: {e}")
            return []

    def fetch_jobs(self, company):
        wp_url = company['url']
        name = company['name']
        
        tenant = company['tenant']
        job_tuples = []
        
        # Small delay to avoid aggressive rate limiting
        time.sleep(RATE_LIMIT_SLEEP)

        # Try to find the actual inhire.app URL in the WP page
        try:
            # Use a more realistic browser session for the WP page too
            wp_headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            }
            resp = self.session.get(wp_url, headers=wp_headers, timeout=INHIRE_TIMEOUT)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                # Look for potential JSON data in scripts
                for script in soup.find_all('script'):
                    if script.string and ('jobs' in script.string or 'vagas' in script.string):
                        # print(f"DEBUG: Found script with 'jobs' or 'vagas' (first 200 chars): {script.string[:200]}")
                        pass
                # Look for links to inhire.app
                app_links = soup.find_all('a', href=lambda x: x and 'inhire.app' in x)
                for al in app_links:
                    href = al.get('href')
                    # Format: https://tenant.inhire.app/... or https://domain.com/...
                    if 'inhire.app' in href:
                        parts = href.split('//')[-1].split('.')
                        if parts[1] == 'inhire' and parts[2] == 'app':
                            tenant = parts[0]
                            break
        except Exception as e:
            logger.debug(f"Could not extract tenant from WP page for {wp_url}: {e}")

        # Inhire API URL
        api_url = "https://api.inhire.app/job-posts/public/pages"
        company_tuple = (tenant, name, None, wp_url, json.dumps(company), self.source_name)
        
        try:
            headers = {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7',
                'dnt': '1',
                'origin': f'https://{tenant}.inhire.app',
                'priority': 'u=1, i',
                'referer': f'https://{tenant}.inhire.app/',
                'sec-ch-ua': '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-site',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
                'x-tenant': tenant
            }
            response = self.session.get(api_url, headers=headers, timeout=INHIRE_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                logger.debug(f"API response for {tenant} keys: {list(data.keys())}")
                if 'data' in data:
                     logger.debug(f"'data' type: {type(data['data'])}")
                     if isinstance(data['data'], list):
                         logger.debug(f"'data' length: {len(data['data'])}")
                     elif isinstance(data['data'], dict):
                         logger.debug(f"'data' keys: {list(data['data'].keys())}")
                
                # Jobs can be in 'data' or 'jobsPage' field
                jobs = data.get('data', data.get('jobsPage', []))
                
                logger.info(f"Found {len(jobs)} jobs for {tenant}")
                if isinstance(jobs, list):
                    for job in jobs:
                        # Inhire uses 'jobId' or 'id', and 'displayName' or 'title'
                        job_id = str(job.get('jobId', job.get('id', '')))
                        job_title = job.get('displayName', job.get('title', 'N/A'))
                        job_type = job.get('type', 'N/A')
                        department = job.get('category', {}).get('name', 'N/A')
                        
                        # Location parsing: "City, ST, BR" or dict
                        loc = job.get('location', 'N/A')
                        workplace_city = 'N/A'
                        workplace_state = 'N/A'
                        
                        if isinstance(loc, dict):
                            workplace_city = loc.get('city', 'N/A')
                            workplace_state = loc.get('state', 'N/A')
                        elif isinstance(loc, str) and loc != 'N/A':
                            parts = [p.strip() for p in loc.split(',')]
                            if len(parts) >= 1: workplace_city = parts[0]
                            if len(parts) >= 2: workplace_state = parts[1]

                        workplace_type = job.get('workplaceType', job.get('workMode', 'N/A'))
                        
                        job_tuples.append((job_id, tenant, job_title, job_type, department, workplace_city, workplace_state, workplace_type, self.source_name))
            elif response.status_code == 403:
                logger.warning(f"Inhire API returned 403 for tenant {tenant}. Skipping.")
            else:
                # Log other non-200 responses
                logger.warning(f"Inhire API returned {response.status_code} for tenant {tenant} (URL: {api_url})")
        except Exception as e:
            logger.error(f"Error processing Inhire jobs for {tenant}: {e}", exc_info=True)
            
        return company_tuple, job_tuples

class LinkedInScraper(Scraper):
    def __init__(self, session):
        super().__init__(session)
        self.source_name = "linkedin"
        self.limit = LINKEDIN_LIMIT
        self.threads = LINKEDIN_THREADS
        self.keywords = LINKEDIN_KEYWORDS
        self.location = LINKEDIN_LOCATION

    def fetch_companies(self):
        # LinkedIn doesn't have a company list we iterate over, we search by keywords.
        # We'll return a single "dummy" company representing the search query.
        return [{
            'id': 'linkedin_search',
            'name': f'LinkedIn Search: {self.keywords} in {self.location}',
            'url': 'https://www.linkedin.com/jobs'
        }]

    def fetch_jobs(self, company):
        job_tuples = []
        company_id = company['id']
        company_name = company['name']
        company_url = company['url']
        
        company_tuple = (company_id, company_name, None, company_url, json.dumps(company), self.source_name)
        
        base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.linkedin.com/jobs/search',
        }

        start = 0
        while len(job_tuples) < self.limit:
            params = {
                'keywords': self.keywords,
                'location': self.location,
                'start': start,
            }
            
            try:
                logger.info(f"Fetching LinkedIn jobs starting at {start}...")
                response = self.session.get(base_url, params=params, headers=headers, timeout=LINKEDIN_TIMEOUT)
                
                if response.status_code == 429:
                    logger.warning("LinkedIn rate limited (429). Stopping for this source.")
                    break
                
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                job_cards = soup.find_all('li')
                
                if not job_cards:
                    logger.info("No more LinkedIn jobs found.")
                    break
                
                for card in job_cards:
                    if len(job_tuples) >= self.limit:
                        break
                        
                    try:
                        # Extract basic info from the card
                        title_tag = card.find('h3', class_='base-search-card__title')
                        company_tag = card.find('h4', class_='base-search-card__subtitle')
                        location_tag = card.find('span', class_='job-search-card__location')
                        link_tag = card.find('a', class_='base-card__full-link')
                        
                        if not title_tag or not link_tag:
                            continue
                            
                        job_title = title_tag.get_text(strip=True)
                        job_company_name = company_tag.get_text(strip=True) if company_tag else "N/A"
                        job_location = location_tag.get_text(strip=True) if location_tag else "N/A"
                        job_link = link_tag.get('href', '').split('?')[0]
                        
                        # Extract Job ID from link (e.g., .../view/123456789)
                        job_id_match = re.search(r'/view/(\d+)', job_link)
                        job_id = job_id_match.group(1) if job_id_match else f"li_{hash(job_link)}"
                        
                        # Parse location
                        parts = [p.strip() for p in job_location.split(',')]
                        city = parts[0] if len(parts) > 0 else "N/A"
                        state = parts[1] if len(parts) > 1 else "N/A"
                        
                        # Default values for fields not easily available in the guest list
                        job_type = "N/A"
                        department = "N/A"
                        workplace_type = "N/A" # Could be parsed from title or card details if present
                        
                        job_tuples.append((job_id, job_company_name, job_title, job_type, department, city, state, workplace_type, self.source_name))
                    
                    except Exception as e:
                        logger.error(f"Error parsing LinkedIn job card: {e}")
                
                start += 25
                time.sleep(RATE_LIMIT_SLEEP) # Respectful delay between pages
                
            except Exception as e:
                logger.error(f"Error fetching LinkedIn jobs: {e}")
                break
                
        return company_tuple, job_tuples

def get_http_session():
    """Create a requests session with retry strategy"""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def init_database_tables(db_path, ts):
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

    # Debug env vars
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

    # Single transaction for all data
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
