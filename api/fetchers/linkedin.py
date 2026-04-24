"""On-demand LinkedIn detail fetcher.

Uses the public `jobs-guest` endpoint documented at
<https://gist.github.com/Diegiwg/51c22fa7ec9d92ed9b5d1f537b9e1107>, which
returns a lightweight HTML fragment with the job description and a criteria
list (seniority, employment type, job function, industries). This replaces
the earlier path that proxied to the Selenium sidecar — no warm driver
required, so the fetch typically completes in under a second."""
import logging
import os
import time

from bs4 import BeautifulSoup

from .base import FetchError, get_http_session

logger = logging.getLogger(__name__)

LINKEDIN_DETAIL_TIMEOUT = int(os.environ.get('LINKEDIN_DETAIL_TIMEOUT', '30'))
GUEST_JOB_URL = 'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{id}'
# LinkedIn serves a shorter/simpler HTML to guest agents but still refuses
# some default python-requests User-Agents. A realistic UA string avoids a
# 429/999 while remaining unauthenticated.
USER_AGENT = (
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)

_CRITERIA_KEYS = {
    'seniority level': 'seniority',
    'employment type': 'employment_type',
    'job function': 'job_function',
    'industries': 'industries',
}


def _extract_description_html(soup: BeautifulSoup) -> str:
    """Return the inner markup of the description container without the
    LinkedIn `show-more-less-html__markup` wrapper (which has clamp/collapse
    CSS we don't want)."""
    node = soup.select_one('[class*=description] > section > div')
    if node is None:
        return ''
    return node.decode_contents().strip()


def _extract_criteria(soup: BeautifulSoup) -> dict:
    """Parse the `description__job-criteria-list` <ul>. Keys are
    lower-cased label → snake_case field name (see `_CRITERIA_KEYS`)."""
    out: dict = {}
    for item in soup.select('ul.description__job-criteria-list > li'):
        label_el = item.find(class_='description__job-criteria-subheader')
        value_el = item.find(class_='description__job-criteria-text')
        if not label_el or not value_el:
            continue
        label = label_el.get_text(strip=True).lower()
        field = _CRITERIA_KEYS.get(label)
        if field:
            out[field] = value_el.get_text(strip=True)
    return out


def fetch_linkedin_detail(job_id: str, context: dict) -> dict:
    url = GUEST_JOB_URL.format(id=job_id)
    logger.info('[linkedin %s] ==> fetch start — %s', job_id, url)
    session = get_http_session()

    logger.info('[linkedin %s] step 1: HTTP GET (timeout=%ds)',
                job_id, LINKEDIN_DETAIL_TIMEOUT)
    t0 = time.monotonic()
    try:
        response = session.get(
            url,
            headers={'User-Agent': USER_AGENT, 'Accept-Language': 'en-US,en;q=0.9'},
            timeout=LINKEDIN_DETAIL_TIMEOUT,
        )
    except Exception as exc:
        raise FetchError(f"GET {url} failed: {exc}") from exc
    logger.info('[linkedin %s] step 1: status=%d size=%d (%.2fs)',
                job_id, response.status_code, len(response.content),
                time.monotonic() - t0)
    if response.status_code != 200:
        raise FetchError(f"GET {url} returned {response.status_code}")

    logger.info('[linkedin %s] step 2: parsing HTML', job_id)
    soup = BeautifulSoup(response.content, 'html.parser')

    description_html = _extract_description_html(soup)
    if not description_html:
        raise FetchError(f"description not found at {url} — page may be auth-gated")

    criteria = _extract_criteria(soup)
    detail_html = response.text

    fields = {
        'description': description_html,
        'seniority': criteria.get('seniority', ''),
        'employment_type': criteria.get('employment_type', ''),
        'job_function': criteria.get('job_function', ''),
        'industries': criteria.get('industries', ''),
        'detail_html': detail_html,
    }
    logger.info(
        '[linkedin %s] <== fetch done — desc=%d detail_html=%d seniority=%r '
        'employment_type=%r job_function=%r industries=%r',
        job_id,
        len(fields['description']),
        len(fields['detail_html']),
        fields['seniority'],
        fields['employment_type'],
        fields['job_function'],
        fields['industries'],
    )
    return fields
