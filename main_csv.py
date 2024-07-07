import requests
import csv
import json
import tqdm
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# CSV file paths
companies_csv_path = 'companies.csv'
jobs_csv_path = 'jobs.csv'

# Function to fetch and process job data
def fetch_and_process_job_data(company):
    company_id = company['companyId']
    company_name = company['careerPageName']
    company_logo_url = company['careerPageLogo']
    company_career_page_url = company['careerPageUrl']
    friendly_badge = company['badges']['friendlyBadge']
    
    company_data = [company_id, company_name, company_logo_url, company_career_page_url, friendly_badge]
    
    job_data_list = []
    
    if company_career_page_url:
        job_url = company_career_page_url
        job_response = requests.get(job_url)
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
                
                job_data_list.append([job_id, company_id, job_title, job_type, department, workplace_city, workplace_state, workplace_type])
    
    return company_data, job_data_list

# Initialize the CSV writers
with open(companies_csv_path, mode='w', newline='', encoding='utf-8') as companies_file, \
     open(jobs_csv_path, mode='w', newline='', encoding='utf-8') as jobs_file:

    companies_writer = csv.writer(companies_file)
    jobs_writer = csv.writer(jobs_file)

    # Write headers for companies CSV
    companies_writer.writerow(['id', 'name', 'logo_url', 'career_page_url', 'friendly_badge'])

    # Write headers for jobs CSV
    jobs_writer.writerow(['id', 'company_id', 'title', 'type', 'department', 'workplace_city', 'workplace_state', 'workplace_type'])

    # URL for the initial company list
    limit = 3000
    url = f'https://portal.api.gupy.io/api/company?limit={limit}'
    response = requests.get(url)
    data = response.json()
    
    companies = data['data']
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_company = {executor.submit(fetch_and_process_job_data, company): company for company in companies}
        
        for future in tqdm.tqdm(as_completed(future_to_company), total=len(companies)):
            try:
                company_data, job_data_list = future.result()
                companies_writer.writerow(company_data)
                for job_data in job_data_list:
                    jobs_writer.writerow(job_data)
            except Exception as exc:
                print(f"Generated an exception: {exc}")
