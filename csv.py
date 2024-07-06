import requests
import tqdm
from bs4 import BeautifulSoup
import json
import csv

# CSV file paths
companies_csv_path = 'companies.csv'
jobs_csv_path = 'jobs.csv'

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

    for company_data in tqdm.tqdm(data['data']):
        # Extract company information
        company_id = company_data['companyId']
        company_name = company_data['careerPageName']
        company_logo_url = company_data['careerPageLogo']
        company_career_page_url = company_data['careerPageUrl']
        friendly_badge = company_data['badges']['friendlyBadge']

        print(f"Company: [{company_id}] \t{company_name}")

        # Write company information to the CSV file
        companies_writer.writerow([company_id, company_name, company_logo_url, company_career_page_url, friendly_badge])

        if company_career_page_url == '':
            continue

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

                # Write job information to the CSV file
                jobs_writer.writerow([job_id, company_id, job_title, job_type, department, workplace_city, workplace_state, workplace_type])
