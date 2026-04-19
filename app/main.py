#!/usr/bin/env python
import os
import sys

import requests
import json
import sqlite3
import tqdm
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
import os
import sys
import threading

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Error: two arguments are required.")
        sys.exit(1)

ts = sys.argv[1]
folder = sys.argv[2]
db_file = sys.argv[3]

# Database configuration
company_limit = int(os.environ.get('GUPY_COMPANY_LIMIT', 3))
threads = int(os.environ.get('GUPY_THREADS', 16))
db_path = os.path.join(folder, db_file)

# Thread-safe database connection
db_lock = threading.Lock()

def init_database_tables(db_path, ts):
    """Initialize the SQLite database with basic tables only"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()    
    
    # Create companies table
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS companies_{ts} (
            id TEXT PRIMARY KEY,
            name TEXT,            
            logo_url TEXT,
            career_page_url TEXT,
            company_data TEXT
        )
    """)
    
    # Create jobs table
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

def insert_company_data(db_path, company_id, company_name, company_career_page_url, company_data, ts):
    """Thread-safe insert of company data"""
    with db_lock:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        sql = f"""
            INSERT OR IGNORE INTO companies_{ts} (id, name, career_page_url, company_data)
            VALUES (?, ?, ?, ?)
        """
        values = (company_id, company_name, company_career_page_url, company_data)
        cursor.execute(sql, values)
        conn.commit()
        conn.close()

def insert_job_data(db_path, job_data_list):
    """Thread-safe insert of job data"""
    if not job_data_list:
        return
        
    with db_lock:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()        

        cursor.executemany(f"""
            INSERT OR IGNORE INTO jobs_{ts}
            (id, company_id, title, type, department, workplace_city, workplace_state, workplace_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, job_data_list)
        
        conn.commit()
        conn.close()

def fetch_and_process_job_data(company, db_path, ts):
    """Fetch and process job data for a company"""
    company_id = company['companyId']
    company_name = company['careerPageName']
    company_logo_url = company['careerPageLogo']
    company_career_page_url = company['careerPageUrl']
    friendly_badge = company['badges']['friendlyBadge']
    company_data = json.dumps(company)
    
    # Insert company data immediately    
    insert_company_data(db_path, company_id, company_name, company_career_page_url, company_data, ts)
    jobs_data_list = []    
    
    if company_career_page_url:
        try:
            job_url = company_career_page_url
            job_response = requests.get(job_url, timeout=30)
            soup = BeautifulSoup(job_response.content, 'html.parser')
            script_tag = soup.find('script', {'id': '__NEXT_DATA__'})            
            if script_tag:
                script_content = script_tag.contents[0]
                script_json = json.loads(script_content)
                
                job_data = script_json.get('props', {}).get('pageProps', {}).get('jobs', [])
                carrerpage_data = script_json.get('props', {}).get('pageProps', {}).get('careerPage', {})
                canonicalUrl = script_json.get('props', {}).get('pageProps', {}).get('canonicalUrl', {})
                job_data_list = []
                for job in job_data:
                    job_full = { 'job': job, 'careerPage': carrerpage_data, 'url': canonicalUrl }
                    job_json = json.dumps(job_full)
                    
                    job_id = job.get('id', '')
                    job_title = job.get('title', 'N/A')
                    job_type = job.get('type', 'N/A')
                    department = job.get('department', 'N/A')                    
                    workplace_city = job.get('workplace', {}).get('address', {}).get('city', 'N/A')
                    workplace_state = job.get('workplace', {}).get('address', {}).get('state', 'N/A')
                    workplace_type = job.get('workplace', {}).get('workplaceType', 'N/A')
                    
                    job_data_list.append((job_id, company_id, job_title, job_type, department, workplace_city, workplace_state, workplace_type))
        
        except Exception as e:
            print(f"Error processing jobs for company {company_id}: {e}")
    
    # Insert job data if any found
    if job_data_list:
        insert_job_data(db_path, job_data_list)        
    
    return len(job_data_list)

# Main execution
if __name__ == "__main__":
    # Create output folder
    os.makedirs(folder, exist_ok=True)
    
    # Initialize database with tables only
    init_database_tables(db_path, ts)
    
    # URL for the initial company list
    url = f'https://portal.api.gupy.io/api/company?limit={company_limit}'
    response = requests.get(url)
    data = response.json()
    
    companies = data['data']
    
    total_jobs = 0
    
    with ThreadPoolExecutor(max_workers=threads) as executor:
        future_to_company = {executor.submit(fetch_and_process_job_data, company, db_path, ts): company for company in companies}
        
        for future in tqdm.tqdm(as_completed(future_to_company), total=len(companies), miniters=int(threads/2)):
            try:
                job_count = future.result()
                total_jobs += job_count
            except Exception as exc:
                print(f"Generated an exception: {exc}")



    print(f"total jobs: {total_jobs}")
