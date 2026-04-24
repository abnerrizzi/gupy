import json
import logging
import time

from .base import FetchError, get_http_session

logger = logging.getLogger(__name__)

INHIRE_TIMEOUT = 30


def fetch_inhire_detail(job_id: str, context: dict) -> dict:
    tenant = context.get('company_id') or ''
    if not tenant:
        raise FetchError(f"no tenant (company_id) stored for inhire job {job_id}")

    api_url = f"https://api.inhire.app/job-posts/public/pages/{job_id}"
    headers = {
        'accept': 'application/json, text/plain, */*',
        'origin': f'https://{tenant}.inhire.app',
        'referer': f'https://{tenant}.inhire.app/',
        'x-tenant': tenant,
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) jobhubmine-detail-fetch',
    }

    logger.info('[inhire %s] ==> fetch start — tenant=%s url=%s', job_id, tenant, api_url)
    session = get_http_session()

    logger.info('[inhire %s] step 1: HTTP GET', job_id)
    t0 = time.monotonic()
    try:
        response = session.get(api_url, headers=headers, timeout=INHIRE_TIMEOUT)
    except Exception as exc:
        raise FetchError(f"GET {api_url} failed: {exc}") from exc
    logger.info('[inhire %s] step 1: status=%d size=%d (%.1fs)',
                job_id, response.status_code, len(response.content), time.monotonic() - t0)
    if response.status_code != 200:
        raise FetchError(f"GET {api_url} returned {response.status_code}")

    raw_body = response.text
    logger.info('[inhire %s] step 2: parsing JSON', job_id)
    try:
        data = response.json()
    except ValueError as exc:
        raise FetchError(f"non-JSON body at {api_url}: {exc}") from exc

    # Inhire occasionally wraps the payload in `data`. Accept both shapes.
    payload = data.get('data') if isinstance(data.get('data'), dict) else data

    contract = payload.get('contractType')
    if isinstance(contract, list):
        contract = ', '.join(str(c) for c in contract if c)
    elif contract is None:
        contract = ''

    # Persist the normalised payload (post data-wrapper unwrapping) as the
    # raw_payload so the UI tree view sees the job object directly.
    raw_payload = (
        json.dumps(payload, ensure_ascii=False)
        if payload is not data
        else raw_body
    )

    fields = {
        'description_html': payload.get('description') or '',
        'about_html': payload.get('about') or '',
        'contract_type': contract,
        'workplace_type': payload.get('workplaceType') or '',
        'location': payload.get('location') or '',
        'location_complement': payload.get('locationComplement') or '',
        'published_at': payload.get('publishedAt') or '',
        'raw_payload': raw_payload,
    }
    logger.info('[inhire %s] <== fetch done — desc=%d about=%d raw_payload=%d',
                job_id,
                len(fields['description_html']),
                len(fields['about_html']),
                len(fields['raw_payload']))
    return fields
