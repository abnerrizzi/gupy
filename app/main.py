import os
import sys
import requests
import json
import sqlite3
import tqdm
import threading
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# Constants
COMPANY_LIMIT = int(os.environ.get('GUPY_COMPANY_LIMIT', 3))
THREADS = int(os.environ.get('GUPY_THREADS', 16))

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
            company_data TEXT
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
            workplace_type TEXT
        )
    """)
    conn.commit()
    conn.close()

def fetch_and_process_job_data(company):
    """Fetch and process job data for a company (No DB operations)"""
    company_id = company['companyId']
    company_name = company['careerPageName']
    company_career_page_url = company['careerPageUrl']
    company_data = json.dumps(company)
    
    company_tuple = (company_id, company_name, company_career_page_url, company_data)
    job_tuples = []
    
    if company_career_page_url:
        try:
            session = get_http_session()
            job_response = session.get(company_career_page_url, timeout=15)
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
                    
                    job_tuples.append((job_id, company_id, job_title, job_type, department, workplace_city, workplace_state, workplace_type))
        
        except Exception as e:
            print(f"Error processing jobs for company {company_id}: {e}")
    
    return company_tuple, job_tuples

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Error: Usage: main.py <ts> <folder> <db_file>")
        sys.exit(1)

    ts = sys.argv[1]
    folder = sys.argv[2]
    db_file = sys.argv[3]
    db_path = os.path.join(folder, db_file)

    os.makedirs(folder, exist_ok=True)
    init_database_tables(db_path, ts)
    
    url = f'https://portal.api.gupy.io/api/company?limit={COMPANY_LIMIT}'
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        companies = response.json().get('data', [])
    except Exception as e:
        print(f"Failed to fetch company list: {e}")
        sys.exit(1)
    
    all_companies = []
    all_jobs = []
    
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        future_to_company = {executor.submit(fetch_and_process_job_data, company): company for company in companies}
        
        for future in tqdm.tqdm(as_completed(future_to_company), total=len(companies)):
            try:
                company_tuple, job_tuples = future.result()
                all_companies.append(company_tuple)
                all_jobs.extend(job_tuples)
            except Exception as exc:
                print(f"Worker generated an exception: {exc}")

    # Single transaction for all data
    print(f"Inserting data into database: {len(all_companies)} companies, {len(all_jobs)} jobs...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.executemany(f"INSERT OR IGNORE INTO companies_{ts} (id, name, career_page_url, company_data) VALUES (?, ?, ?, ?)", all_companies)
        cursor.executemany(f"INSERT OR IGNORE INTO jobs_{ts} (id, company_id, title, type, department, workplace_city, workplace_state, workplace_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", all_jobs)
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
        conn.rollback()
    finally:
        conn.close()

    print(f"Total jobs scraped: {len(all_jobs)}")
