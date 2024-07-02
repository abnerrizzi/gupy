import requests
import sqlite3
import tqdm
from bs4 import BeautifulSoup
import json

class DatabaseManager:
    def __init__(self, db_path='gupy_data.db'):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY UNIQUE,
                name TEXT NOT NULL,
                logo_url TEXT,
                career_page_url TEXT,
                friendly_badge BOOLEAN
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY UNIQUE,
                company_id INTEGER,
                title TEXT NOT NULL,
                type TEXT,
                department TEXT,
                workplace_city TEXT,
                workplace_state TEXT,
                workplace_type TEXT,
                FOREIGN KEY (company_id) REFERENCES companies (id)
            )
        ''')
        self.conn.commit()

    def insert_company(self, id, name, logo_url, career_page_url, friendly_badge):
        self.cursor.execute('''
            INSERT OR REPLACE INTO companies (id, name, logo_url, career_page_url, friendly_badge)
            VALUES (?, ?, ?, ?, ?)
        ''', (id, name, logo_url, career_page_url, friendly_badge))
        self.conn.commit()
        return self.cursor.lastrowid

    def insert_job(self, job_id, company_id, title, job_type, department, workplace_city, workplace_state, workplace_type):
        self.cursor.execute('''
            INSERT OR REPLACE INTO jobs (id, company_id, title, type, department, workplace_city, workplace_state, workplace_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (job_id, company_id, title, job_type, department, workplace_city, workplace_state, workplace_type))
        self.conn.commit()

# URL for the initial company list
limit = 23
url = f'https://portal.api.gupy.io/api/company?limit={limit}'
response = requests.get(url)
data = response.json()

# Initialize the DatabaseManager
db_manager = DatabaseManager()

for company_data in tqdm.tqdm(data['data']):
    # Extract company information
    company_id = company_data['companyId']
    company_name = company_data['careerPageName']
    company_logo_url = company_data['careerPageLogo']
    company_career_page_url = company_data['careerPageUrl']
    friendly_badge = company_data['badges']['friendlyBadge']

    # print(f"Company: [{company_id}] \t{company_name}")

    # Insert company information into the database
    company_id = db_manager.insert_company(
        company_id,
        company_name,
        company_logo_url,
        company_career_page_url,
        friendly_badge
    )

    if company_career_page_url == '':
        continue
    if (0 == 0):

        # Fetch and process job data from the career page URL
        job_url = company_career_page_url
        job_response = requests.get(job_url)
        soup = BeautifulSoup(job_response.content, 'html.parser')

        # Find the script tag with id '__NEXT_DATA__'
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})

        if script_tag:
            # Extract the JSON content from the script tag
            script_content = script_tag.contents[0]
            script_json = json.loads(script_content)

            # Access the required job information
            job_data = script_json.get('props', {}).get('pageProps', {}).get('jobs', [])

            for job in tqdm.tqdm(job_data, leave=False):
                job_id = job.get('id', '')
                job_title = job.get('title', 'N/A')
                job_type = job.get('type', 'N/A')
                department = job.get('department', 'N/A')
                workplace_city = job.get('workplace', {}).get('address', {}).get('city', 'N/A')
                workplace_state = job.get('workplace', {}).get('address', {}).get('state', 'N/A')
                workplace_type = job.get('workplace', {}).get('workplaceType', 'N/A')

                # Insert job information into the database
                db_manager.insert_job(
                    job_id,
                    company_id,
                    job_title,
                    job_type,
                    department,
                    workplace_city,
                    workplace_state,
                    workplace_type
                )

# Close the database connection
db_manager.conn.close()
