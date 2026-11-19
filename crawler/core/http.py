"""Fetching pages politely and reliably.

HttpFetcher guarantees for every request:
  * robots.txt is checked (if enabled in the source config); Crawl-delay is honored
  * at least `delay_seconds` (+ random jitter) between requests
  * retries with exponential backoff on network errors, 429 and 5xx; Retry-After is honored
  * 404/410 raise NotFound immediately (the posting was removed — not worth retrying)

Other fetchers (e.g. a Playwright one for JavaScript-only sites) implement the same `Fetcher` protocol,
so sources do not care how a page is downloaded.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Protocol
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from crawler.config import HttpConfig

log = logging.getLogger(__name__)

RETRY_STATUSES = {429, 500, 502, 503, 504}


class FetchError(Exception):
    """Page could not be downloaded"""


class NotFound(FetchError):
    """404 / 410 — the page does not exist"""


class RobotsDisallowed(FetchError):
    """robots.txt does not allow us to fetch this URL"""


class Fetcher(Protocol):
    def get(self, url: str) -> str: ...
    def close(self) -> None: ...


class HttpFetcher:
    def __init__(self, config: HttpConfig, client: httpx.Client | None = None):
        self.config = config
        self._client = client or httpx.Client(
            headers={
                "User-Agent": config.user_agent,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "fi,en;q=0.8",
            },
            timeout=config.timeout_seconds,
            follow_redirects=True,
        )
        self._robots: dict[str, RobotFileParser | None] = {}
        self._delay = config.delay_seconds
        self._last_request = 0.0
        self.requests_made = 0

    def get(self, url: str) -> str:
        if self.config.respect_robots_txt and not self._allowed(url):
            raise RobotsDisallowed(f"robots.txt disallows {url}")

        attempts = self.config.max_retries + 1
        for attempt in range(1, attempts + 1):
            self._wait()
            try:
                response = self._client.get(url)
            except httpx.TransportError as exc:
                if attempt == attempts:
                    raise FetchError(f"{url}: {exc.__class__.__name__}: {exc}") from exc
                self._backoff(attempt, url, str(exc))
                continue

            if response.status_code in (404, 410):
                raise NotFound(f"{url}: HTTP {response.status_code}")
            if response.status_code in RETRY_STATUSES and attempt < attempts:
                self._backoff(attempt, url, f"HTTP {response.status_code}", response.headers.get("Retry-After"))
                continue
            if response.status_code >= 400:
                raise FetchError(f"{url}: HTTP {response.status_code}")
            return response.text

        raise FetchError(f"{url}: giving up after {attempts} attempts")

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HttpFetcher:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _wait(self) -> None:
        pause = self._delay + random.uniform(0, self.config.jitter_seconds)
        elapsed = time.monotonic() - self._last_request
        if self._last_request and elapsed < pause:
            time.sleep(pause - elapsed)
        self._last_request = time.monotonic()
        self.requests_made += 1

    def _backoff(self, attempt: int, url: str, reason: str, retry_after: str | None = None) -> None:
        delay = self.config.backoff_seconds * 2 ** (attempt - 1)
        if retry_after and retry_after.isdigit():
            delay = max(delay, min(float(retry_after), 300))
        log.warning("retry %d/%d in %.1fs for %s (%s)", attempt, self.config.max_retries, delay, url, reason)
        time.sleep(delay)

    def _allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            self._robots[origin] = self._load_robots(origin)
        parser = self._robots[origin]
        return parser is None or parser.can_fetch(self.config.user_agent, url)

    def _load_robots(self, origin: str) -> RobotFileParser | None:
        robots_url = f"{origin}/robots.txt"
        try:
            self._wait()
            response = self._client.get(robots_url)
        except httpx.TransportError as exc:
            log.warning("could not load %s (%s); continuing without robots rules", robots_url, exc)
            return None
        if response.status_code >= 400:
            log.info("%s returned HTTP %d; no robots rules apply", robots_url, response.status_code)
            return None
        parser = RobotFileParser(robots_url)
        parser.parse(response.text.splitlines())
        crawl_delay = parser.crawl_delay(self.config.user_agent)
        if crawl_delay and float(crawl_delay) > self._delay:
            log.info("robots.txt Crawl-delay %ss is above our delay; using it", crawl_delay)
            self._delay = float(crawl_delay)
        return parser


def create_fetcher(kind: str, config: HttpConfig) -> Fetcher:
    if kind == "http":
        return HttpFetcher(config)
    if kind == "playwright":
        raise NotImplementedError(
            "Playwright fetcher is not implemented yet: no current source needs JavaScript rendering "
        )
    raise ValueError(f"unknown fetcher: {kind}")
