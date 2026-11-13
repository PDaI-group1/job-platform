import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

from crawler.config import SourceConfig
from crawler.core.http import Fetcher
from crawler.schemas import RawJob

log = logging.getLogger(__name__)


class ParseError(Exception):
    """A page was downloaded but does not have the expected structure."""


class BaseSource(ABC):
    name: ClassVar[str]
    required_listing_selectors: ClassVar[tuple[str, ...]] = ()
    required_detail_selectors: ClassVar[tuple[str, ...]] = ()

    def __init__(self, config: SourceConfig, fetcher: Fetcher | None, dump_dir: Path | None = None):
        self.config = config
        self.fetcher = fetcher
        self.dump_dir = dump_dir
        self._check_config()

    @abstractmethod
    def iter_listing(self, start_page: int = 0, max_pages: int | None = None) -> Iterator[RawJob]:
        """Yield jobs from listing pages, page by page, until the last page or max_pages."""

    @abstractmethod
    def fetch_detail(self, job: RawJob) -> RawJob:
        """Download and parse the job's own page, return `job` merged with it. Raises FetchError / ParseError."""

    @abstractmethod
    def parse_listing_page(self, html: str, url: str) -> tuple[list[RawJob], bool]:
        """jobs on the page, whether a next page exists. Pure: no network."""

    @abstractmethod
    def parse_detail_page(self, html: str, job: RawJob) -> RawJob:
        """Detail-page data only, identity copied from  job. Pure: no network."""


    def get(self, url: str, kind: str) -> str:
        if self.fetcher is None:
            raise RuntimeError(f"{self.name}: source was created without a fetcher (parse-only mode)")
        html = self.fetcher.get(url)
        if self.dump_dir:
            self._dump(url, kind, html)
        return html

    def _dump(self, url: str, kind: str, html: str) -> None:
        name = re.sub(r"[^\w.-]+", "_", url.split("://", 1)[-1])[:150]
        path = self.dump_dir / self.name / kind / f"{name}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")

    def _check_config(self) -> None:
        missing = [s for s in self.required_listing_selectors if s not in self.config.listing.selectors]
        missing += [s for s in self.required_detail_selectors if s not in self.config.detail.selectors]
        if missing:
            raise ValueError(f"{self.name}: selectors missing in config: {', '.join(missing)}")
