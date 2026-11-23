from __future__ import annotations

from crawler.config import Employer
from crawler.core.feed import FeedSource
from crawler.schemas import RawJob
from crawler.sources.teamtailor.parsers import location_texts, parse_feed


class TeamtailorSource(FeedSource):
    name = "teamtailor"
    feed_ext = "rss"

    def parse_feed(self, text: str, employer: Employer) -> list[RawJob]:
        return parse_feed(text, employer)

    def location_texts(self, job: RawJob) -> list[str]:
        return location_texts(job)
