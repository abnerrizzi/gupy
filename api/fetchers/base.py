import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class FetchError(Exception):
    """Raised when a detail fetch fails for an expected reason (HTTP error,
    missing payload, upstream rate-limit). Maps to a 502 in the API layer."""


def get_http_session() -> requests.Session:
    """HTTP session with retry/backoff — mirrors app/scrapers/base.py."""
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
