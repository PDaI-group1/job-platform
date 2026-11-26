from __future__ import annotations

import logging
import re
from abc import abstractmethod
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import ClassVar

from crawler.config import Employer, NormalizationRules, SourceConfig, load_normalization_rules
from crawler.core.base import BaseSource, ParseError
from crawler.core.http import Fetcher, FetchError, NotFound, RobotsDisallowed
from crawler.schemas import RawJob

log = logging.getLogger(__name__)

_FINLAND_CODES = {"fi", "fin", "finland", "suomi"}


class FeedSource(BaseSource):
    feed_ext: ClassVar[str] = "json"

    def __init__(
        self,
        config: SourceConfig,
        fetcher: Fetcher | None,
        dump_dir: Path | None = None,
        employers: Iterable[str] | None = None,
        rules: NormalizationRules | None = None,
    ):
        super().__init__(config, fetcher, dump_dir)
        if config.feed is None:
            raise ValueError(f"{self.name}: source config has no `feed` section")
        self.feed = config.feed
        rules = rules or load_normalization_rules()
        self._finland = re.compile(rules.feed_filters.finland_pattern, re.IGNORECASE)
        self._skip_titles = [re.compile(p, re.IGNORECASE) for p in rules.feed_filters.skip_title_patterns]
        self.employers = self._select_employers(employers)
        self.partial_run = employers is not None


    @abstractmethod
    def parse_feed(self, text: str, employer: Employer) -> list[RawJob]:
        """All jobs of the feed, unfiltered. Raises ParseError if the text is not a valid feed."""

    @abstractmethod
    def location_texts(self, job: RawJob) -> list[str]:
        """Every location-like text of the job (city, office, country) for the Finland filter."""

    def iter_listing(self, start_page: int = 0, max_pages: int | None = None) -> Iterator[RawJob]:
        employers = self.employers[start_page:]
        if max_pages is not None:
            employers = employers[:max_pages]
        for employer in employers:
            jobs = self._fetch_employer(employer)
            if jobs is None:
                continue
            kept = [j for j in jobs if self._keep(j, employer)]
            log.info("%s: %d jobs, %d kept (Finland, no open applications)", employer.name, len(jobs), len(kept))
            yield from kept

    def fetch_detail(self, job: RawJob) -> RawJob:
        return job

    def parse_listing_page(self, html: str, url: str) -> tuple[list[RawJob], bool]:
        employer = self._employer_for_url(url)
        return [j for j in self.parse_feed(html, employer) if self._keep(j, employer, log_skips=False)], False

    def parse_detail_page(self, html: str, job: RawJob) -> RawJob:
        raise NotImplementedError(f"{self.name} is a feed source: there are no detail pages")

    def feed_urls(self, employer: Employer) -> list[str]:
        values = {"token": employer.token or "", "url": (employer.url or "").rstrip("/")}
        return [template.format(**values) for template in self.feed.urls]

    def is_finland(self, job: RawJob) -> bool:
        for text in self.location_texts(job):
            text = text.strip()
            if text.lower() in _FINLAND_CODES or self._finland.search(text):
                return True
        return False

    def _fetch_employer(self, employer: Employer) -> list[RawJob] | None:
        empty: list[RawJob] | None = None
        problems: list[str] = []
        for url in self.feed_urls(employer):
            try:
                jobs = self.parse_feed(self.get(url, "feed", self.feed_ext), employer)
            except RobotsDisallowed:
                raise
            except NotFound:
                problems.append(f"{url}: not found")
                continue
            except (FetchError, ParseError) as exc:
                problems.append(str(exc))
                continue
            if jobs:
                return jobs
            empty = jobs
        if empty is not None:
            log.info("%s: the feed is empty", employer.name)
            return empty
        message = f"{employer.name}: no working feed ({'; '.join(problems)})"
        self.errors.append(message)
        log.warning(message)
        return None

    def _keep(self, job: RawJob, employer: Employer, log_skips: bool = True) -> bool:
        title = job.title or ""
        if self.feed.skip_open_applications and any(p.search(title) for p in self._skip_titles):
            if log_skips:
                log.debug("%s: skipping open application %r", employer.name, title)
            return False
        return not self.feed.finland_only or self.is_finland(job)

    def _select_employers(self, wanted: Iterable[str] | None) -> list[Employer]:
        if wanted is None:
            return list(self.config.employers)
        by_key = {e.key.lower(): e for e in self.config.employers}
        selected, unknown = [], []
        for key in wanted:
            (selected.append(by_key[key.lower()]) if key.lower() in by_key else unknown.append(key))
        if unknown:
            raise ValueError(f"unknown {self.name} employer(s): {', '.join(unknown)}; "
                             f"available: {', '.join(sorted(by_key))}")
        return selected

    def _employer_for_url(self, url: str) -> Employer:
        for employer in self.config.employers:
            if url and url in self.feed_urls(employer):
                return employer
        return Employer(name="", token="unknown")
