from __future__ import annotations

from crawler.config import Employer
from crawler.core.feed import FeedSource
from crawler.schemas import RawJob
from crawler.sources.greenhouse.parsers import location_texts, parse_jobs


class GreenhouseSource(FeedSource):
    name = "greenhouse"
    feed_ext = "json"

    def parse_feed(self, text: str, employer: Employer) -> list[RawJob]:
        return parse_jobs(text, employer)

    def location_texts(self, job: RawJob) -> list[str]:
        return location_texts(job)
