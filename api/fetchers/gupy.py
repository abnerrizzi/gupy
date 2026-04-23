import json
import logging
import re
import time

from bs4 import BeautifulSoup

from .base import FetchError, get_http_session

logger = logging.getLogger(__name__)

GUPY_TIMEOUT = 30


def _derive_job_url(context: dict, job_id: str) -> str:
    career = context.get('career_page_url') or ''
    if career:
        # The Gupy career page is https://{sub}.gupy.io[/{opaque}]. Strip any
        # opaque path so /jobs/{id} resolves correctly.
        match = re.match(r'^(https?://[^/]+)', career)
        base = match.group(1) if match else career.rstrip('/')
        return f"{base}/jobs/{job_id}"
    return f"https://portal.gupy.io/job/{job_id}"


def fetch_gupy_detail(job_id: str, context: dict) -> dict:
    url = _derive_job_url(context, job_id)
    logger.info('[gupy %s] ==> fetch start — %s', job_id, url)
    session = get_http_session()

    logger.info('[gupy %s] step 1: HTTP GET', job_id)
    t0 = time.monotonic()
    try:
        response = session.get(url, timeout=GUPY_TIMEOUT)
    except Exception as exc:
        raise FetchError(f"GET {url} failed: {exc}") from exc
    logger.info('[gupy %s] step 1: status=%d size=%d (%.1fs)',
                job_id, response.status_code, len(response.content), time.monotonic() - t0)
    if response.status_code != 200:
        raise FetchError(f"GET {url} returned {response.status_code}")

    logger.info('[gupy %s] step 2: locating __NEXT_DATA__ script tag', job_id)
    soup = BeautifulSoup(response.content, 'html.parser')
    script = soup.find('script', {'id': '__NEXT_DATA__'})
    if not script or not script.string:
        raise FetchError(f"__NEXT_DATA__ not found at {url}")
    raw_next_data = script.string
    logger.info('[gupy %s] step 2: __NEXT_DATA__ found bytes=%d',
                job_id, len(raw_next_data))

    logger.info('[gupy %s] step 3: parsing JSON payload', job_id)
    try:
        data = json.loads(raw_next_data)
        job = data['props']['pageProps']['job']
    except (KeyError, json.JSONDecodeError) as exc:
        raise FetchError(f"malformed __NEXT_DATA__ at {url}: {exc}") from exc

    fields = {
        'description_html': job.get('description') or '',
        'responsibilities_html': job.get('responsibilities') or '',
        'prerequisites_html': job.get('prerequisites') or '',
        'workplace_type': job.get('workplaceType') or '',
        'job_type': job.get('jobType') or '',
        'country': job.get('addressCountry') or '',
        'published_at': job.get('publishedAt') or '',
        'next_data': raw_next_data,
    }
    logger.info('[gupy %s] <== fetch done — desc=%d resp=%d prereq=%d next_data=%d',
                job_id,
                len(fields['description_html']),
                len(fields['responsibilities_html']),
                len(fields['prerequisites_html']),
                len(fields['next_data']))
    return fields
