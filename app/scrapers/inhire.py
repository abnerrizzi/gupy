import json
import logging
import os
import time
from typing import List, Tuple

import requests
from bs4 import BeautifulSoup

from .base import RATE_LIMIT_SLEEP, Scraper

logger = logging.getLogger(__name__)

INHIRE_LIMIT = int(os.environ.get('INHIRE_COMPANY_LIMIT', 10))
INHIRE_THREADS = int(os.environ.get('INHIRE_THREADS', 16))
INHIRE_TIMEOUT = 15


class InhireScraper(Scraper):
    def __init__(self, session: requests.Session) -> None:
        super().__init__(session)
        self.source_name = "inhire"
        self.limit = INHIRE_LIMIT
        self.threads = INHIRE_THREADS

    def fetch_companies(self) -> list:
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
                    title = link.text.replace('Carreiras | ', '').strip()
                    tenant = href.strip('/').split('/')[-1]

                    companies.append({
                        'tenant': tenant,
                        'name': title,
                        'url': href
                    })
            companies.insert(0, {'tenant': 'yandeh', 'name': 'Yandeh', 'url': 'https://carreira.inhire.com.br/carreiras/yandeh/'})
            limited_companies = companies[:self.limit]
            logger.debug(f"Limited to {len(limited_companies)} companies")
            return limited_companies
        except Exception as e:
            logger.error(f"Failed to fetch Inhire company list: {e}")
            return []

    def fetch_jobs(self, company: dict) -> Tuple[tuple, List[tuple]]:
        wp_url = company['url']
        name = company['name']

        tenant = company['tenant']
        job_tuples: List[tuple] = []

        time.sleep(RATE_LIMIT_SLEEP)

        try:
            wp_headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            }
            resp = self.session.get(wp_url, headers=wp_headers, timeout=INHIRE_TIMEOUT)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                for script in soup.find_all('script'):
                    if script.string and ('jobs' in script.string or 'vagas' in script.string):
                        pass
                app_links = soup.find_all('a', href=lambda x: x and 'inhire.app' in x)
                for al in app_links:
                    href = al.get('href')
                    if 'inhire.app' in href:
                        parts = href.split('//')[-1].split('.')
                        if parts[1] == 'inhire' and parts[2] == 'app':
                            tenant = parts[0]
                            break
        except Exception as e:
            logger.debug(f"Could not extract tenant from WP page for {wp_url}: {e}")

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

                jobs = data.get('data', data.get('jobsPage', []))

                logger.info(f"Found {len(jobs)} jobs for {tenant}")
                if isinstance(jobs, list):
                    for job in jobs:
                        job_id = str(job.get('jobId', job.get('id', '')))
                        job_title = job.get('displayName', job.get('title', 'N/A'))
                        job_type = job.get('type', 'N/A')
                        department = job.get('category', {}).get('name', 'N/A')

                        loc = job.get('location', 'N/A')
                        workplace_city = 'N/A'
                        workplace_state = 'N/A'

                        if isinstance(loc, dict):
                            workplace_city = loc.get('city', 'N/A')
                            workplace_state = loc.get('state', 'N/A')
                        elif isinstance(loc, str) and loc != 'N/A':
                            parts = [p.strip() for p in loc.split(',')]
                            if len(parts) >= 1:
                                workplace_city = parts[0]
                            if len(parts) >= 2:
                                workplace_state = parts[1]

                        workplace_type = job.get('workplaceType', job.get('workMode', 'N/A'))

                        job_tuples.append((job_id, tenant, job_title, job_type, department, workplace_city, workplace_state, workplace_type, self.source_name))
            elif response.status_code == 403:
                logger.warning(f"Inhire API returned 403 for tenant {tenant}. Skipping.")
            else:
                logger.warning(f"Inhire API returned {response.status_code} for tenant {tenant} (URL: {api_url})")
        except Exception as e:
            logger.error(f"Error processing Inhire jobs for {tenant}: {e}", exc_info=True)

        return company_tuple, job_tuples
