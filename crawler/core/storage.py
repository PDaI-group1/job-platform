import json
import logging
from dataclasses import dataclass, fields
from datetime import datetime
from pathlib import Path
from typing import IO

import psycopg
from psycopg.types.json import Jsonb

from crawler.schemas import JobRecord

log = logging.getLogger(__name__)

_COLUMNS = [
    "source", "source_job_id", "url", "title", "company_name", "location", "remote_type", "employment_type",
    "description", "skills", "language", "salary_min", "salary_max", "salary_currency", "salary_period",
    "published_at", "deadline_at", "is_active", "content_hash", "raw_data", "scraped_at",
]
_UPDATABLE = [c for c in _COLUMNS if c not in ("source", "source_job_id")]

_UPSERT_SQL = f"""
INSERT INTO jobs ({", ".join(_COLUMNS)})
VALUES ({", ".join(f"%({c})s" for c in _COLUMNS)})
ON CONFLICT (source, source_job_id) DO UPDATE SET
    {", ".join(f"{c} = EXCLUDED.{c}" for c in _UPDATABLE)}
"""


class StorageError(Exception):
    pass


@dataclass
class SaveResult:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0

    def __iadd__(self, other: SaveResult) -> SaveResult:
        for f in fields(self):
            setattr(self, f.name, getattr(self, f.name) + getattr(other, f.name))
        return self


class PostgresStorage:
    def __init__(self, dsn: str):
        try:
            self._conn = psycopg.connect(dsn, connect_timeout=10)
        except psycopg.OperationalError as exc:
            raise StorageError(f"cannot connect to PostgreSQL: {exc}".strip()) from exc

    def known_ids(self, source: str, complete_only: bool = False) -> set[str]:
        sql = "SELECT source_job_id FROM jobs WHERE source = %s"
        if complete_only:
            sql += " AND description IS NOT NULL"
        with self._conn.cursor() as cur:
            cur.execute(sql, (source,))
            ids = {row[0] for row in cur.fetchall()}
        self._conn.commit()
        return ids

    def save(self, jobs: list[JobRecord], update_existing: bool = True) -> SaveResult:
        if not jobs:
            return SaveResult()
        sources = {j.source for j in jobs}
        if len(sources) != 1:
            raise StorageError(f"a batch must contain one source, got {sources}")
        source = sources.pop()
        rows = {j.source_job_id: j.to_db_row() for j in jobs}  # dedupe inside the batch, last wins

        try:
            with self._conn.transaction(), self._conn.cursor() as cur:
                cur.execute(
                    "SELECT source_job_id, content_hash FROM jobs WHERE source = %s AND source_job_id = ANY(%s)",
                    (source, list(rows)),
                )
                existing: dict[str, str | None] = dict(cur.fetchall())

                to_write = [r for jid, r in rows.items()
                            if jid not in existing or (update_existing and existing[jid] != r["content_hash"])]
                write_ids = {r["source_job_id"] for r in to_write}
                to_touch = [jid for jid in rows if jid not in write_ids]

                if to_write:
                    cur.executemany(_UPSERT_SQL, [_adapt(r) for r in to_write])
                if to_touch:
                    scraped_at = max(rows[jid]["scraped_at"] for jid in to_touch)
                    cur.execute(
                        "UPDATE jobs SET scraped_at = %s, is_active = TRUE "
                        "WHERE source = %s AND source_job_id = ANY(%s)",
                        (scraped_at, source, to_touch),
                    )
        except psycopg.Error as exc:
            raise StorageError(f"saving batch of {len(rows)} jobs failed: {exc}".strip()) from exc

        inserted = sum(1 for r in to_write if r["source_job_id"] not in existing)
        return SaveResult(inserted=inserted, updated=len(to_write) - inserted, unchanged=len(to_touch))

    def deactivate_missing(self, source: str, run_started_at: datetime) -> int:
        with self._conn.transaction(), self._conn.cursor() as cur:
            cur.execute(
                "UPDATE jobs SET is_active = FALSE WHERE source = %s AND is_active AND scraped_at < %s",
                (source, run_started_at),
            )
            return cur.rowcount

    def close(self) -> None:
        self._conn.close()


def _adapt(row: dict) -> dict:
    return {**row, "raw_data": Jsonb(row["raw_data"])}


class JsonlWriter:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._fh: IO[str] = path.open("w", encoding="utf-8")
        self.written = 0

    def write(self, jobs: list[JobRecord]) -> None:
        for job in jobs:
            self._fh.write(json.dumps(job.to_json_dict(), ensure_ascii=False) + "\n")
        self._fh.flush()
        self.written += len(jobs)

    def close(self) -> None:
        self._fh.close()
