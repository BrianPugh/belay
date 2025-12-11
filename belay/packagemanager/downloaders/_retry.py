"""Shared retry utilities for downloaders."""

import requests
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)


def _is_retryable_exception(exc: BaseException) -> bool:
    """Determine if an exception should trigger a retry.

    Retries on:
    - Timeout errors
    - Connection errors
    - HTTP 429 (rate limit)
    - HTTP 5xx (server errors)

    Does NOT retry on:
    - HTTP 4xx (client errors, except 429)
    """
    if isinstance(exc, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
        return True
    if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
        status = exc.response.status_code
        return status == 429 or status >= 500
    return False


@retry(
    retry=retry_if_exception(_is_retryable_exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def fetch_url(url: str, timeout: float = 30.0) -> requests.Response:
    """Fetch URL with retries on transient failures.

    Retries up to 3 times with exponential backoff (1s, 2s, 4s... max 10s)
    on timeout, connection errors, rate limits (429), and server errors (5xx).

    Parameters
    ----------
    url
        URL to fetch.
    timeout
        Request timeout in seconds.

    Returns
    -------
    requests.Response
        Response object (may have non-200 status code for 4xx errors).

    Raises
    ------
    requests.exceptions.RequestException
        If request fails after retries.
    """
    response = requests.get(url, timeout=timeout)
    # Raise for 5xx errors and 429 (rate limit) to trigger retry, but not for other 4xx
    if response.status_code >= 500 or response.status_code == 429:
        response.raise_for_status()
    return response
