import os

from .base import FetchError, get_http_session

LINKEDIN_DETAIL_URL = os.environ.get(
    'LINKEDIN_DETAIL_URL', 'http://linkedin-detail:8000'
)
LINKEDIN_DETAIL_TIMEOUT = int(os.environ.get('LINKEDIN_DETAIL_TIMEOUT', '90'))


def fetch_linkedin_detail(job_id: str, context: dict) -> dict:
    url = f"{LINKEDIN_DETAIL_URL.rstrip('/')}/fetch/{job_id}"
    session = get_http_session()
    try:
        response = session.post(url, timeout=LINKEDIN_DETAIL_TIMEOUT)
    except Exception as exc:
        raise FetchError(
            f"POST {url} failed — is the linkedin-detail service up? ({exc})"
        ) from exc
    if response.status_code != 200:
        raise FetchError(
            f"POST {url} returned {response.status_code}: {response.text[:200]}"
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise FetchError(f"non-JSON body at {url}: {exc}") from exc

    return {
        'description': payload.get('description') or '',
        'seniority': payload.get('seniority') or '',
        'employment_type': payload.get('employment_type') or '',
        'detail_html': payload.get('detail_html') or '',
    }
