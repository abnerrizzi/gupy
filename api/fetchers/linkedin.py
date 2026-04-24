import logging
import os
import time

from .base import FetchError, get_http_session

logger = logging.getLogger(__name__)

LINKEDIN_DETAIL_URL = os.environ.get(
    'LINKEDIN_DETAIL_URL', 'http://linkedin-detail:8000'
)
LINKEDIN_DETAIL_TIMEOUT = int(os.environ.get('LINKEDIN_DETAIL_TIMEOUT', '90'))


def fetch_linkedin_detail(job_id: str, context: dict) -> dict:
    url = f"{LINKEDIN_DETAIL_URL.rstrip('/')}/fetch/{job_id}"
    logger.info('[linkedin %s] ==> proxy fetch start', job_id)
    logger.info('[linkedin %s] step 1: POST %s (timeout=%ds)',
                job_id, url, LINKEDIN_DETAIL_TIMEOUT)
    session = get_http_session()
    t0 = time.monotonic()
    try:
        response = session.post(url, timeout=LINKEDIN_DETAIL_TIMEOUT)
    except Exception as exc:
        raise FetchError(
            f"POST {url} failed — is the linkedin-detail service up? ({exc})"
        ) from exc
    elapsed = time.monotonic() - t0
    logger.info('[linkedin %s] step 1: sidecar responded status=%d size=%d (%.2fs)',
                job_id, response.status_code, len(response.content), elapsed)
    if response.status_code != 200:
        raise FetchError(
            f"POST {url} returned {response.status_code}: {response.text[:200]}"
        )

    logger.info('[linkedin %s] step 2: parsing sidecar JSON', job_id)
    try:
        payload = response.json()
    except ValueError as exc:
        raise FetchError(f"non-JSON body at {url}: {exc}") from exc

    fields = {
        'description': payload.get('description') or '',
        'seniority': payload.get('seniority') or '',
        'employment_type': payload.get('employment_type') or '',
        'detail_html': payload.get('detail_html') or '',
    }
    logger.info('[linkedin %s] <== proxy fetch done — desc=%d detail_html=%d '
                'seniority=%r employment_type=%r',
                job_id,
                len(fields['description']),
                len(fields['detail_html']),
                fields['seniority'],
                fields['employment_type'])
    return fields
