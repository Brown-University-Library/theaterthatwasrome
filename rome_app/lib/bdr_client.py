import logging

import httpx2
from django.conf import settings

logger = logging.getLogger('rome')


class BdrUnavailable(Exception):
    """
    Identifies a temporary failure while contacting BDR.
    """


def request(method: str, url: str, *, data: dict[str, str] | None = None, allow_not_found: bool = False) -> httpx2.Response:
    """
    Contacts BDR with explicit timeouts and no automatic retries.
    Called by: models BDR wrappers, annotation_helpers.fetch_url_content()
    """
    timeout = httpx2.Timeout(
        settings.BDR_READ_TIMEOUT, connect=settings.BDR_CONNECT_TIMEOUT, pool=settings.BDR_CONNECT_TIMEOUT
    )
    try:
        ## Follow read redirects as before; never replay an annotation write after a redirect.
        with httpx2.Client(timeout=timeout, follow_redirects=method == 'GET') as client:
            response = client.request(method, url, data=data)
    except (httpx2.TimeoutException, httpx2.NetworkError, httpx2.RemoteProtocolError) as exc:
        logger.warning('BDR unavailable: method, ``%s``; reason, ``%s``', method, type(exc).__name__)
        raise BdrUnavailable('BDR could not be reached.') from exc

    if response.status_code in {500, 502, 503, 504}:
        logger.warning('BDR unavailable: method, ``%s``; status_code, ``%s``', method, response.status_code)
        raise BdrUnavailable('BDR is temporarily unavailable.')
    if not (allow_not_found and response.status_code == 404):
        response.raise_for_status()
    return response
