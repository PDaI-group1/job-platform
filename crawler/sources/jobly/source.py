import logging
from collections.abc import Iterator
from urllib.parse import urlencode, urlsplit, urlunsplit

from crawler.core.base import BaseSource
from crawler.schemas import RawJob
from crawler.sources.jobly.parsers import parse_detail, parse_listing

log = logging.getLogger(__name__)


class JoblySource(BaseSource):
    name = "jobly"
    required_listing_selectors = ("item", "link")
    required_detail_selectors = ("body",)

    def page_url(self, page_index: int) -> str:
        listing = self.config.listing
        value = listing.first_page + page_index
        if page_index == 0 and listing.first_page == 0:
            return listing.start_url
        parts = urlsplit(listing.start_url)
        query = f"{parts.query}&" if parts.query else ""
        return urlunsplit(parts._replace(query=query + urlencode({listing.page_param: value})))

    def iter_listing(self, start_page: int = 0, max_pages: int | None = None) -> Iterator[RawJob]:
        page_index, pages_done = start_page, 0
        while max_pages is None or pages_done < max_pages:
            url = self.page_url(page_index)
            jobs, has_next = self.parse_listing_page(self.get(url, "listing"), url)
            log.info("listing page %d: %d jobs", page_index + 1, len(jobs))
            if not jobs:
                log.info("empty listing page, stopping")
                return
            yield from jobs
            pages_done += 1
            if not has_next:
                log.info("no next page link, reached the end of the listing")
                return
            page_index += 1

    def fetch_detail(self, job: RawJob) -> RawJob:
        detail = self.parse_detail_page(self.get(job.url, "detail"), job)
        if job.salary_text and detail.salary_text:
            detail = detail.model_copy(update={
                "salary_text": None,
                "extra": {**detail.extra, "salary_detail_text": detail.salary_text},
            })
        return job.merged(detail)

    def parse_listing_page(self, html: str, url: str) -> tuple[list[RawJob], bool]:
        page = parse_listing(html, self.config, url)
        if page.skipped:
            log.warning("%d items on %s could not be parsed", page.skipped, url)
        return page.jobs, page.has_next

    def parse_detail_page(self, html: str, job: RawJob) -> RawJob:
        return parse_detail(html, self.config, job)
