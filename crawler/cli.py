import argparse
import json
import logging
import os
import sys
from pathlib import Path

from crawler import __version__
from crawler.config import ConfigError, load_normalization_rules, load_source_config
from crawler.core.feed import FeedSource
from crawler.core.http import create_fetcher
from crawler.core.pipeline import Mode, Pipeline, RunOptions
from crawler.core.storage import JsonlWriter, PostgresStorage, StorageError
from crawler.normalize import NormalizationError, normalize_job
from crawler.schemas import RawJob
from crawler.sources import GROUPS, SOURCES, expand_sources, get_source_class

log = logging.getLogger("crawler")


def _positive_int(value: str) -> int:
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return n


def _non_negative_float(value: str) -> float:
    n = float(value)
    if n < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return n


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m crawler", description="Job platform job crawler")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--log-level", default=os.getenv("CRAWLER_LOG_LEVEL", "INFO"), choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("sources", help="list available sources")

    run = sub.add_parser("run", help="crawl a source and save jobs", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    run.add_argument("source", nargs="+", choices=[*sorted(SOURCES), *GROUPS],
                     help="one or more sources; 'feeds' = greenhouse lever teamtailor, 'all' = every source")
    run.add_argument("--employer", action="append", metavar="KEY",
                     help="feed sources only: crawl just this employer (repeatable), e.g. --employer oura")
    run.add_argument("--mode", type=Mode, choices=[m.value for m in Mode], default=Mode.INCREMENTAL.value,
                     help="listing: list pages only; incremental: detail pages for new jobs; full: everything")
    run.add_argument("--limit", type=_positive_int, help="stop after this many jobs")
    run.add_argument("--start-page", type=_positive_int, default=1, help="first listing page")
    run.add_argument("--max-pages", type=_positive_int, help="stop after this many listing pages")
    run.add_argument("--delay", type=_non_negative_float, help="seconds between requests")
    run.add_argument("--batch-size", type=_positive_int, default=50, help="jobs per database transaction")
    run.add_argument("--dry-run", action="store_true", help="do not write to the database")
    run.add_argument("--output", type=Path, help="also write normalized jobs to this JSONL file")
    run.add_argument("--dump-html", type=Path, metavar="DIR", help="save every fetched page into DIR")
    run.add_argument("--deactivate-missing", action="store_true", help="mark jobs not seen in this run as inactive")
    run.add_argument("--fail-fast", action="store_true", help="stop on the first parse/validation error")
    run.add_argument("--no-robots", action="store_true", help="ignore robots.txt")
    run.add_argument("--config", type=Path, help="path to a source YAML")
    run.add_argument("--database-url", default=None, help="PostgreSQL URL")
    run.add_argument("--stats-json", type=Path, help="write run statistics to this JSON file")
    parse = sub.add_parser("parse", help="run a parser on a saved HTML file and print the result")
    parse.add_argument("source", choices=sorted(SOURCES))
    parse.add_argument("file", type=Path)
    parse.add_argument("--kind", choices=["listing", "detail"], required=True)
    parse.add_argument("--url", default="https://example.com/job-0",
                       help="page URL (detail pages), or the feed URL to pick the employer (feed sources)")
    parse.add_argument("--normalized", action="store_true", help="print normalized records instead of raw")
    return parser


def cmd_sources() -> int:
    for name in SOURCES:
        cfg = load_source_config(name)
        if cfg.feed:
            print(f"{name:12} {cfg.display_name:12} {len(cfg.employers)} employers: "
                  f"{', '.join(e.key for e in cfg.employers)}")
        else:
            print(f"{name:12} {cfg.display_name:12} {cfg.listing.start_url}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    names = expand_sources(args.source)
    if args.config and len(names) > 1:
        log.error("--config works with a single source")
        return 2
    feed_names = [n for n in names if issubclass(get_source_class(n), FeedSource)]
    if args.employer and len(feed_names) != 1:
        log.error("--employer needs exactly one feed source, e.g. run greenhouse --employer oura")
        return 2

    writer = JsonlWriter(args.output) if args.output else None
    codes = []
    try:
        for name in names:
            codes.append(run_source(name, args, writer))
    finally:
        if writer:
            writer.close()
    # 130 if interrupted, 1 if any source failed completely, else 0
    return 130 if 130 in codes else max(codes)


def run_source(name: str, args: argparse.Namespace, writer: JsonlWriter | None) -> int:
    config = load_source_config(name, args.config)
    http_overrides = {}
    if args.delay is not None:
        http_overrides["delay_seconds"] = args.delay
    if args.no_robots:
        http_overrides["respect_robots_txt"] = False
    if http_overrides:
        config = config.model_copy(update={"http": config.http.model_copy(update=http_overrides)})
    rules = load_normalization_rules()

    storage = None
    if not args.dry_run:
        dsn = args.database_url or os.getenv("DATABASE_URL")
        if not dsn:
            log.error("no database: set DATABASE_URL, pass --database-url, or use --dry-run")
            return 1
        storage = PostgresStorage(dsn)
    fetcher = create_fetcher(config.fetcher, config.http)

    options = RunOptions(
        mode=args.mode,
        limit=args.limit,
        start_page=args.start_page - 1,
        max_pages=args.max_pages,
        batch_size=args.batch_size,
        deactivate_missing=args.deactivate_missing,
        fail_fast=args.fail_fast,
    )
    source_cls = get_source_class(name)
    if issubclass(source_cls, FeedSource):
        try:
            source = source_cls(config, fetcher, dump_dir=args.dump_html, employers=args.employer, rules=rules)
        except ValueError as exc:
            fetcher.close()
            if storage:
                storage.close()
            log.error("%s", exc)
            return 2
    else:
        source = source_cls(config, fetcher, dump_dir=args.dump_html)
    log.info("crawling %s: mode=%s limit=%s pages=%s dry_run=%s",
             name, options.mode.value, options.limit, options.max_pages or "all", args.dry_run)
    try:
        stats = Pipeline(source, rules, storage, writer).run(options)
    finally:
        fetcher.close()
        if storage:
            storage.close()

    summary = stats.summary()
    log.info("done %s: %s", name, ", ".join(f"{k}={v}" for k, v in summary.items() if v not in (0, False, None)))
    for error in stats.errors[:10]:
        log.info("  error: %s", error)
    if args.stats_json:
        path = args.stats_json if len(expand_sources(args.source)) == 1 else \
            args.stats_json.with_name(f"{args.stats_json.stem}_{name}{args.stats_json.suffix}")
        path.write_text(json.dumps({**summary, "error_messages": stats.errors}, indent=2), encoding="utf-8")
    if stats.interrupted:
        return 130
    return 1 if stats.listed == 0 and stats.errors else 0


def cmd_parse(args: argparse.Namespace) -> int:
    config = load_source_config(args.source)
    source = get_source_class(args.source)(config, fetcher=None)
    html = args.file.read_text(encoding="utf-8")
    if isinstance(source, FeedSource):
        if args.kind != "listing":
            log.error("%s is a feed source: use --kind listing", args.source)
            return 2
        raws, _ = source.parse_listing_page(html, args.url)
    elif args.kind == "listing":
        raws, _ = source.parse_listing_page(html, config.listing.start_url)
    else:
        job_id = args.url.rstrip("/").rsplit("-", 1)[-1]
        stub = RawJob(source=config.name, source_job_id=job_id, url=args.url)
        raws = [stub.merged(source.parse_detail_page(html, stub))]

    rules = load_normalization_rules()
    for raw in raws:
        if args.normalized:
            try:
                print(json.dumps(normalize_job(raw, rules).to_json_dict(), ensure_ascii=False, indent=2))
            except NormalizationError as exc:
                print(f"INVALID: {exc}", file=sys.stderr)
        else:
            print(raw.model_dump_json(indent=2))
    return 0


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def load_env() -> None:
    try:
        from dotenv import find_dotenv, load_dotenv
    except ImportError:
        return
    load_dotenv(find_dotenv(usecwd=True), override=False)


def main(argv: list[str] | None = None) -> int:
    load_env()
    args = build_parser().parse_args(argv)
    setup_logging(args.log_level)
    try:
        if args.command == "sources":
            return cmd_sources()
        if args.command == "run":
            return cmd_run(args)
        if args.command == "parse":
            return cmd_parse(args)
    except (ConfigError, StorageError) as exc:
        log.error("%s", exc)
        return 1
    except KeyboardInterrupt:
        return 130
    return 2
