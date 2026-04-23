import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

RATE_LIMIT_SLEEP = 2


class Scraper:
    def __init__(self, session: requests.Session) -> None:
        self.session = session
        self.source_name = "unknown"
        self.limit = 30
        self.threads = 1

    def fetch_companies(self) -> list:
        raise NotImplementedError

    def fetch_jobs(self, company: dict) -> tuple:
        raise NotImplementedError


def get_http_session() -> requests.Session:
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
