from __future__ import annotations

from crawler.config import Employer
from crawler.core.feed import FeedSource
from crawler.schemas import RawJob
from crawler.sources.lever.parsers import location_texts, parse_postings


class LeverSource(FeedSource):
    name = "lever"
    feed_ext = "json"

    def parse_feed(self, text: str, employer: Employer) -> list[RawJob]:
        return parse_postings(text, employer)

    def location_texts(self, job: RawJob) -> list[str]:
        return location_texts(job)
