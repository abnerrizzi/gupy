#!/usr/bin/env python
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
    if len(sys.argv) != 3:
        print("Error: two arguments are required.")
        sys.exit(1)

ts = sys.argv[1]
folder = sys.argv[2]

# Database configuration
company_limit = 3000
threads = 16
db_path = f'{folder}/{ts}-gupy_direct.db'

# Thread-safe database connection
db_lock = threading.Lock()

def init_database_tables(db_path):
    """Initialize the SQLite database with basic tables only"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop existing tables
    cursor.execute("DROP TABLE IF EXISTS companies")
    cursor.execute("DROP TABLE IF EXISTS jobs")
    
    # Create companies table
    cursor.execute("""
        CREATE TABLE companies (
            id TEXT PRIMARY KEY,
            name TEXT,
            logo_url TEXT,
            career_page_url TEXT,
            friendly_badge TEXT
        )
    """)
    
    # Create jobs table
    cursor.execute("""
        CREATE TABLE jobs (
            id TEXT PRIMARY KEY,
            company_id TEXT,
            title TEXT,
            type TEXT,
            department TEXT,
            workplace_city TEXT,
            workplace_state TEXT,
            workplace_type TEXT,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    """)
    
    conn.commit()
    conn.close()

def insert_company_data(db_path, company_data):
    """Thread-safe insert of company data"""
    with db_lock:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR IGNORE INTO companies 
            (id, name, logo_url, career_page_url, friendly_badge)
            VALUES (?, ?, ?, ?, ?)
        """, company_data)
        
        conn.commit()
        conn.close()

def insert_job_data(db_path, job_data_list):
    """Thread-safe insert of job data"""
    if not job_data_list:
        return
        
    with db_lock:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.executemany("""
            INSERT OR IGNORE INTO jobs 
            (id, company_id, title, type, department, workplace_city, workplace_state, workplace_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, job_data_list)
        
        conn.commit()
        conn.close()

def fetch_and_process_job_data(company, db_path):
    """Fetch and process job data for a company"""
    company_id = company['companyId']
    company_name = company['careerPageName']
    company_logo_url = company['careerPageLogo']
    company_career_page_url = company['careerPageUrl']
    friendly_badge = company['badges']['friendlyBadge']
    
    company_data = (company_id, company_name, company_logo_url, company_career_page_url, friendly_badge)
    
    # Insert company data immediately
    insert_company_data(db_path, company_data)
    
    job_data_list = []
    
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
                
                for job in job_data:
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
    init_database_tables(db_path)
    
    # URL for the initial company list
    url = f'https://portal.api.gupy.io/api/company?limit={company_limit}'
    response = requests.get(url)
    data = response.json()
    
    companies = data['data']
    
    total_jobs = 0
    
    with ThreadPoolExecutor(max_workers=threads) as executor:
        future_to_company = {executor.submit(fetch_and_process_job_data, company, db_path): company for company in companies}
        
        for future in tqdm.tqdm(as_completed(future_to_company), total=len(companies), miniters=int(50)):
            try:
                job_count = future.result()
                total_jobs += job_count
            except Exception as exc:
                print(f"Generated an exception: {exc}")