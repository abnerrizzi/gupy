"""On-demand detail fetchers, one per source.

Each fetcher is a callable `(job_id: str, context: dict) -> dict` where the
returned dict's keys must match the non-`id`/`fetched_at` columns of
`jobs_{source}_detail`. FetchError signals a soft failure that should surface
to the client as a 502."""

from .base import FetchError
from .gupy import fetch_gupy_detail
from .inhire import fetch_inhire_detail
from .linkedin import fetch_linkedin_detail

FETCHERS = {
    'gupy': fetch_gupy_detail,
    'inhire': fetch_inhire_detail,
    'linkedin': fetch_linkedin_detail,
}

__all__ = ['FETCHERS', 'FetchError']
