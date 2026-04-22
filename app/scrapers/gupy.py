import json
import logging
import os
from typing import List, Tuple

import requests
from bs4 import BeautifulSoup

from .base import Scraper

logger = logging.getLogger(__name__)

GUPY_LIMIT = int(os.environ.get('GUPY_COMPANY_LIMIT', 30))
GUPY_THREADS = int(os.environ.get('GUPY_THREADS', 16))
GUPY_TIMEOUT = 30


class GupyScraper(Scraper):
    def __init__(self, session: requests.Session) -> None:
        super().__init__(session)
        self.source_name = "gupy"
        self.limit = GUPY_LIMIT
        self.threads = GUPY_THREADS

    def fetch_companies(self) -> list:
        url = f'https://portal.api.gupy.io/api/company?limit={self.limit}'
        try:
            response = self.session.get(url, timeout=GUPY_TIMEOUT)
            response.raise_for_status()
            return response.json().get('data', [])
        except Exception as e:
            logger.error(f"Failed to fetch Gupy company list: {e}")
            return []

    def fetch_jobs(self, company: dict) -> Tuple[tuple, List[tuple]]:
        company_id = company['companyId']
        company_name = company['careerPageName']
        company_career_page_url = company['careerPageUrl']
        company_data = json.dumps(company)

        company_tuple = (company_id, company_name, None, company_career_page_url, company_data, self.source_name)
        job_tuples: List[tuple] = []

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
