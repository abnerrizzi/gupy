import json
import logging
import os
import re
import time
from typing import List, Tuple

import requests
from bs4 import BeautifulSoup

from .base import RATE_LIMIT_SLEEP, Scraper

logger = logging.getLogger(__name__)

LINKEDIN_LIMIT = int(os.environ.get('LINKEDIN_COMPANY_LIMIT', 100))
LINKEDIN_THREADS = int(os.environ.get('LINKEDIN_THREADS', 2))
LINKEDIN_KEYWORDS = os.environ.get('LINKEDIN_KEYWORDS', 'Software Engineer')
LINKEDIN_LOCATION = os.environ.get('LINKEDIN_LOCATION', 'Brazil')
LINKEDIN_TIMEOUT = 30


class LinkedInScraper(Scraper):
    def __init__(self, session: requests.Session) -> None:
        super().__init__(session)
        self.source_name = "linkedin"
        self.limit = LINKEDIN_LIMIT
        self.threads = LINKEDIN_THREADS
        self.keywords = LINKEDIN_KEYWORDS
        self.location = LINKEDIN_LOCATION

    def fetch_companies(self) -> list:
        return [{
            'id': 'linkedin_search',
            'name': f'LinkedIn Search: {self.keywords} in {self.location}',
            'url': 'https://www.linkedin.com/jobs'
        }]

    def fetch_jobs(self, company: dict) -> Tuple[tuple, List[tuple]]:
        job_tuples: List[tuple] = []
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

                        job_id_match = re.search(r'/view/(\d+)', job_link)
                        job_id = job_id_match.group(1) if job_id_match else f"li_{hash(job_link)}"

                        parts = [p.strip() for p in job_location.split(',')]
                        city = parts[0] if len(parts) > 0 else "N/A"
                        state = parts[1] if len(parts) > 1 else "N/A"

                        job_type = "N/A"
                        department = "N/A"
                        workplace_type = "N/A"

                        job_tuples.append((job_id, job_company_name, job_title, job_type, department, city, state, workplace_type, self.source_name))

                    except Exception as e:
                        logger.error(f"Error parsing LinkedIn job card: {e}")

                start += 25
                time.sleep(RATE_LIMIT_SLEEP)

            except Exception as e:
                logger.error(f"Error fetching LinkedIn jobs: {e}")
                break

        return company_tuple, job_tuples
