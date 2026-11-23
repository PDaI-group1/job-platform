import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum

from crawler.config import NormalizationRules
from crawler.core.base import BaseSource, ParseError
from crawler.core.http import FetchError, NotFound, RobotsDisallowed
from crawler.core.storage import JsonlWriter, PostgresStorage, SaveResult
from crawler.normalize import NormalizationError, normalize_job
from crawler.schemas import JobRecord, RawJob

log = logging.getLogger(__name__)


class Mode(StrEnum):
    LISTING = "listing"
    INCREMENTAL = "incremental"
    FULL = "full"


@dataclass
class RunOptions:
    mode: Mode = Mode.INCREMENTAL
    limit: int | None = None
    start_page: int = 0
    max_pages: int | None = None
    batch_size: int = 50
    deactivate_missing: bool = False
    fail_fast: bool = False

    @property
    def is_complete_crawl(self) -> bool:
        return self.limit is None and self.max_pages is None and self.start_page == 0


@dataclass
class RunStats:
    source: str
    mode: str
    listed: int = 0
    duplicates_in_run: int = 0
    details_fetched: int = 0
    details_skipped_known: int = 0
    details_failed: int = 0
    details_gone: int = 0
    details_disallowed: int = 0
    invalid: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    written_to_file: int = 0
    deactivated: int = 0
    requests: int = 0
    duration_seconds: float = 0.0
    interrupted: bool = False
    errors: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        if len(self.errors) < 50:
            self.errors.append(message)

    def summary(self) -> dict:
        data = asdict(self)
        data["errors"] = len(self.errors)
        return data


class Pipeline:
    def __init__(
        self,
        source: BaseSource,
        rules: NormalizationRules,
        storage: PostgresStorage | None = None,
        writer: JsonlWriter | None = None,
    ):
        self.source = source
        self.rules = rules
        self.storage = storage
        self.writer = writer

    def run(self, options: RunOptions) -> RunStats:
        stats = RunStats(source=self.source.name, mode=options.mode.value)
        started_at = datetime.now(timezone.utc)
        t0 = time.monotonic()
        known: set[str] = set()
        if self.storage and options.mode == Mode.INCREMENTAL:
            known = self.storage.known_ids(self.source.name, complete_only=True)
            log.info("%d %s jobs with full data already in the database", len(known), self.source.name)

        seen: set[str] = set()
        batch: list[JobRecord] = []
        try:
            for raw in self.source.iter_listing(options.start_page, options.max_pages):
                if options.limit is not None and stats.listed >= options.limit:
                    log.info("limit of %d jobs reached", options.limit)
                    break
                if raw.source_job_id in seen:
                    stats.duplicates_in_run += 1
                    continue
                seen.add(raw.source_job_id)
                stats.listed += 1

                raw = self._maybe_fetch_detail(raw, options, known, stats)
                if raw is None:
                    continue
                job = self._normalize(raw, stats, options)
                if job is None:
                    continue
                batch.append(job)
                if len(batch) >= options.batch_size:
                    self._flush(batch, options, stats)
                    batch = []
        except KeyboardInterrupt:
            stats.interrupted = True
            log.warning("interrupted, saving what was collected so far…")
        except RobotsDisallowed as exc:
            stats.add_error(str(exc))
            log.error("%s — stopping", exc)
        finally:
            self._flush(batch, options, stats)
            self._finish(options, stats, started_at)
            stats.requests = getattr(self.source.fetcher, "requests_made", 0)
            stats.duration_seconds = round(time.monotonic() - t0, 1)
        return stats


    def _maybe_fetch_detail(self, raw: RawJob, options: RunOptions, known: set[str], stats: RunStats) -> RawJob | None:
        if options.mode == Mode.LISTING:
            return raw
        if options.mode == Mode.INCREMENTAL and raw.source_job_id in known:
            stats.details_skipped_known += 1
            return raw
        try:
            raw = self.source.fetch_detail(raw)
            stats.details_fetched += 1
        except NotFound:
            stats.details_gone += 1
            log.info("job %s disappeared before we opened it, skipping", raw.source_job_id)
            return None
        except RobotsDisallowed:
            stats.details_disallowed += 1
            log.info("robots.txt disallows the page of job %s, skipping it", raw.source_job_id)
            return None
        except (FetchError, ParseError) as exc:
            stats.details_failed += 1
            stats.add_error(f"detail {raw.source_job_id}: {exc}")
            log.warning("detail page failed for %s, keeping listing data: %s", raw.source_job_id, exc)
            if options.fail_fast:
                raise
        return raw

    def _normalize(self, raw: RawJob, stats: RunStats, options: RunOptions) -> JobRecord | None:
        try:
            return normalize_job(raw, self.rules)
        except NormalizationError as exc:
            stats.invalid += 1
            stats.add_error(str(exc))
            log.warning("invalid job skipped: %s", exc)
            if options.fail_fast:
                raise
            return None

    def _flush(self, batch: list[JobRecord], options: RunOptions, stats: RunStats) -> None:
        if not batch:
            return
        if self.writer:
            self.writer.write(batch)
            stats.written_to_file += len(batch)
        if self.storage:
            complete = [j for j in batch if j.raw_data.get("detail_fetched")]
            partial = [j for j in batch if not j.raw_data.get("detail_fetched")]
            result = SaveResult()
            result += self.storage.save(complete, update_existing=True)
            result += self.storage.save(partial, update_existing=False)
            stats.inserted += result.inserted
            stats.updated += result.updated
            stats.unchanged += result.unchanged
            log.info("saved batch of %d: %d new, %d updated, %d unchanged",
                     len(batch), result.inserted, result.updated, result.unchanged)

    def _finish(self, options: RunOptions, stats: RunStats, started_at: datetime) -> None:
        if not (options.deactivate_missing and self.storage):
            return
        if not options.is_complete_crawl:
            log.warning("--deactivate-missing ignored: only valid for a complete crawl (no limit / page range)")
            return
        if stats.interrupted or (stats.errors and stats.listed == 0):
            log.warning("run did not finish cleanly, NOT deactivating missing jobs")
            return
        stats.deactivated = self.storage.deactivate_missing(self.source.name, started_at)
        log.info("%d jobs no longer listed were marked inactive", stats.deactivated)
