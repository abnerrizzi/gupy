import os
import sys
import requests
import json
import sqlite3
import tqdm
import threading
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# Constants
COMPANY_LIMIT = int(os.environ.get('GUPY_COMPANY_LIMIT', 30))
THREADS = int(os.environ.get('GUPY_THREADS', 16))

class Scraper:
    def __init__(self, session):
        self.session = session
        self.source_name = "unknown"

    def fetch_companies(self):
        raise NotImplementedError

    def fetch_jobs(self, company):
        raise NotImplementedError

class GupyScraper(Scraper):
    def __init__(self, session):
        super().__init__(session)
        self.source_name = "gupy"

    def fetch_companies(self):
        # We use a separate limit for Gupy if needed, but here we respect COMPANY_LIMIT
        url = f'https://portal.api.gupy.io/api/company?limit={COMPANY_LIMIT}'
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json().get('data', [])
        except Exception as e:
            print(f"Failed to fetch Gupy company list: {e}")
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
                job_response = self.session.get(company_career_page_url, timeout=15)
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
                        workplace_city = job.get('workplace', {}).get('address', {}).get('city', 'N/A')
                        workplace_state = job.get('workplace', {}).get('address', {}).get('state', 'N/A')
                        workplace_type = job.get('workplace', {}).get('workplaceType', 'N/A')
                        
                        job_tuples.append((job_id, company_id, job_title, job_type, department, workplace_city, workplace_state, workplace_type, self.source_name))
            
            except Exception as e:
                print(f"Error processing Gupy jobs for company {company_id}: {e}")
        
        return company_tuple, job_tuples

class InhireScraper(Scraper):
    def __init__(self, session):
        super().__init__(session)
        self.source_name = "inhire"

    def fetch_companies(self):
        url = "https://carreira.inhire.com.br/carreiras/"
        try:
            response = self.session.get(url, timeout=30)
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
            # For Inhire, we fetch all by default as they are fewer than Gupy
            limited_companies = companies[:COMPANY_LIMIT]
            print(f"DEBUG: Limited to {len(limited_companies)} companies")
            return limited_companies
        except Exception as e:
            print(f"Failed to fetch Inhire company list: {e}")
            return []

    def fetch_jobs(self, company):
        wp_url = company['url']
        name = company['name']
        
        tenant = company['tenant']
        job_tuples = []
        
        # Small delay to avoid aggressive rate limiting
        time.sleep(2)

        # Try to find the actual inhire.app URL in the WP page
        try:
            # Use a more realistic browser session for the WP page too
            wp_headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            }
            resp = self.session.get(wp_url, headers=wp_headers, timeout=10)
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
        except:
            pass

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
            response = self.session.get(api_url, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                print(f"DEBUG: API response for {tenant} keys: {list(data.keys())}")
                if 'data' in data:
                     print(f"DEBUG: 'data' type: {type(data['data'])}")
                     if isinstance(data['data'], list):
                         print(f"DEBUG: 'data' length: {len(data['data'])}")
                     elif isinstance(data['data'], dict):
                         print(f"DEBUG: 'data' keys: {list(data['data'].keys())}")
                
                # Jobs can be in 'data' or 'jobsPage' field
                jobs = data.get('data', data.get('jobsPage', []))
                
                print(f"DEBUG: Found {len(jobs)} jobs for {tenant}")
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
                print(f"ERROR: Inhire API returned 403 for tenant {tenant}. Skipping.")
            else:
                # Log other non-200 responses
                print(f"Inhire API returned {response.status_code} for tenant {tenant} (URL: {api_url})")
        except Exception as e:
            print(f"Error processing Inhire jobs for {tenant}: {e}")
            
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
        print("Error: Usage: main.py <ts> <folder> <db_file>")
        sys.exit(1)

    ts = sys.argv[1]
    folder = sys.argv[2]
    db_file = sys.argv[3]
    db_path = os.path.join(folder, db_file)

    # Debug env vars
    print(f"GUPY_ENABLED: {os.environ.get('GUPY_ENABLED')}")
    print(f"INHIRE_ENABLED: {os.environ.get('INHIRE_ENABLED')}")

    os.makedirs(folder, exist_ok=True)
    init_database_tables(db_path, ts)
    
    session = get_http_session()
    
    gupy_enabled = os.environ.get('GUPY_ENABLED', 'true').lower() == 'true'
    inhire_enabled = os.environ.get('INHIRE_ENABLED', 'true').lower() == 'true'

    scrapers = []
    if gupy_enabled:
        scrapers.append(GupyScraper(session))
    if inhire_enabled:
        scrapers.append(InhireScraper(session))
    
    if not scrapers:
        print("No scrapers enabled. Exiting.")
        sys.exit(0)
    
    all_companies = []
    all_jobs = []
    
    for scraper in scrapers:
        print(f"Fetching companies from {scraper.source_name}...")
        companies = scraper.fetch_companies()
        print(f"Found {len(companies)} companies in {scraper.source_name}")
        
        scraper_companies = 0
        scraper_jobs = 0
        
        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            future_to_company = {executor.submit(scraper.fetch_jobs, company): company for company in companies}
            
            for future in tqdm.tqdm(as_completed(future_to_company), total=len(companies), desc=f"Scraping {scraper.source_name}"):
                try:
                    company_tuple, job_tuples = future.result()
                    all_companies.append(company_tuple)
                    all_jobs.extend(job_tuples)
                    scraper_companies += 1
                    scraper_jobs += len(job_tuples)
                except Exception as exc:
                    print(f"Worker generated an exception: {exc}")
        
        print(f"Collected {scraper_jobs} jobs from {scraper_companies} companies for {scraper.source_name}")

    # Single transaction for all data
    print(f"Inserting data into database: {len(all_companies)} companies, {len(all_jobs)} jobs...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.executemany(f"INSERT OR IGNORE INTO companies_{ts} (id, name, logo_url, career_page_url, company_data, source) VALUES (?, ?, ?, ?, ?, ?)", all_companies)
        cursor.executemany(f"INSERT OR IGNORE INTO jobs_{ts} (id, company_id, title, type, department, workplace_city, workplace_state, workplace_type, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", all_jobs)
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
        conn.rollback()
    finally:
        conn.close()

    print(f"Total jobs scraped: {len(all_jobs)}")
