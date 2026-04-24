"""On-demand LinkedIn detail fetcher.

Uses the public `jobs-guest` endpoint documented at
<https://gist.github.com/Diegiwg/51c22fa7ec9d92ed9b5d1f537b9e1107>, which
returns a lightweight HTML fragment with the job description and a criteria
list (seniority, employment type, job function, industries). This replaces
the earlier path that proxied to the Selenium sidecar — no warm driver
required, so the fetch typically completes in under a second."""
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone

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

_RELATIVE_UNITS = {
    'minute': 'minutes',
    'hour': 'hours',
    'day': 'days',
    'week': 'weeks',
    'month': 'days',    # timedelta lacks months; approximate as 30 days
    'year': 'days',     # approximate as 365 days
}
_RELATIVE_MULTIPLIER = {'month': 30, 'year': 365}


def _parse_posted_time_ago(text: str) -> str:
    """Convert LinkedIn's relative timestamp ("19 hours ago", "3 days ago",
    "Just now") into an ISO-8601 UTC datetime. Returns '' if the text can't
    be parsed — LinkedIn's guest page only gives relative precision so the
    result is approximate by design."""
    if not text:
        return ''
    t = text.strip().lower()
    if 'just' in t or 'moments ago' in t:
        return datetime.now(timezone.utc).isoformat(timespec='seconds')
    m = re.match(r'^(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago', t)
    if not m:
        return ''
    n = int(m.group(1))
    unit = m.group(2)
    if unit in _RELATIVE_MULTIPLIER:
        n *= _RELATIVE_MULTIPLIER[unit]
    kwargs = {_RELATIVE_UNITS[unit]: n}
    dt = datetime.now(timezone.utc) - timedelta(**kwargs)
    return dt.isoformat(timespec='seconds')


def _parse_applicants(text: str) -> int | None:
    """Extract the integer from "Over 200 applicants", "155 applicants", or
    "1 applicant". Returns None if no number is present."""
    if not text:
        return None
    m = re.search(r'(\d+)', text)
    return int(m.group(1)) if m else None


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

    posted_raw = ''
    posted_el = soup.select_one('[class*=posted-time-ago__text]')
    if posted_el:
        posted_raw = posted_el.get_text(strip=True)
    posted_at = _parse_posted_time_ago(posted_raw)

    applicants_raw = ''
    applicants_el = soup.select_one(
        '[class*=num-applicants__caption], [class*=num-applicants__figure]'
    )
    if applicants_el:
        applicants_raw = applicants_el.get_text(' ', strip=True)
    num_applicants = _parse_applicants(applicants_raw)

    fields = {
        'description': description_html,
        'seniority': criteria.get('seniority', ''),
        'employment_type': criteria.get('employment_type', ''),
        'job_function': criteria.get('job_function', ''),
        'industries': criteria.get('industries', ''),
        'posted_at': posted_at,
        'num_applicants': num_applicants,
        'detail_html': detail_html,
    }
    logger.info(
        '[linkedin %s] <== fetch done — desc=%d detail_html=%d seniority=%r '
        'employment_type=%r job_function=%r industries=%r '
        'posted=%r→%s applicants=%r→%s',
        job_id,
        len(fields['description']),
        len(fields['detail_html']),
        fields['seniority'],
        fields['employment_type'],
        fields['job_function'],
        fields['industries'],
        posted_raw, posted_at or '-',
        applicants_raw, num_applicants,
    )
    return fields
