import json
import re

from bs4 import BeautifulSoup

from .base import FetchError, get_http_session

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
    session = get_http_session()
    try:
        response = session.get(url, timeout=GUPY_TIMEOUT)
    except Exception as exc:
        raise FetchError(f"GET {url} failed: {exc}") from exc
    if response.status_code != 200:
        raise FetchError(f"GET {url} returned {response.status_code}")

    soup = BeautifulSoup(response.content, 'html.parser')
    script = soup.find('script', {'id': '__NEXT_DATA__'})
    if not script or not script.string:
        raise FetchError(f"__NEXT_DATA__ not found at {url}")
    try:
        data = json.loads(script.string)
        job = data['props']['pageProps']['job']
    except (KeyError, json.JSONDecodeError) as exc:
        raise FetchError(f"malformed __NEXT_DATA__ at {url}: {exc}") from exc

    return {
        'description_html': job.get('description') or '',
        'responsibilities_html': job.get('responsibilities') or '',
        'prerequisites_html': job.get('prerequisites') or '',
        'workplace_type': job.get('workplaceType') or '',
        'job_type': job.get('jobType') or '',
        'country': job.get('addressCountry') or '',
        'published_at': job.get('publishedAt') or '',
    }
