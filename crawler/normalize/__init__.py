from datetime import datetime, timezone

from pydantic import ValidationError

from crawler.config import NormalizationRules
from crawler.normalize.classify import (
    classify_employment,
    classify_remote,
    detect_language,
)
from crawler.normalize.dates import parse_datetime
from crawler.normalize.salary import parse_salary
from crawler.normalize.text import (
    clean_company,
    clean_location,
    clean_multiline,
    clean_text,
)
from crawler.schemas import JobRecord, RawJob

__all__ = ["normalize_job", "NormalizationError"]


class NormalizationError(Exception):
    def __init__(self, raw: RawJob, reason: str):
        super().__init__(f"{raw.source}:{raw.source_job_id}: {reason}")
        self.raw = raw
        self.reason = reason


def normalize_job(raw: RawJob, rules: NormalizationRules, scraped_at: datetime | None = None) -> JobRecord:
    title = clean_text(raw.title)
    if not title:
        raise NormalizationError(raw, "missing title")

    location = clean_location(raw.location)
    description = clean_multiline(raw.description, rules.max_description_length)
    neg = rules.negation

    remote_type = classify_remote([raw.work_mode_text, title, location, description], rules.remote_type, neg)
    employment_type = classify_employment([raw.employment_type_text, title, description], rules.employment_type, neg)
    language = detect_language(f"{title}\n{description or ''}", rules.language, raw.language_hint)
    salary = parse_salary(raw.salary_text, rules.salary, raw.salary_period_text)

    try:
        return JobRecord(
            source=raw.source,
            source_job_id=raw.source_job_id,
            url=raw.url,
            title=title,
            company_name=clean_company(raw.company),
            location=location,
            remote_type=remote_type,
            employment_type=employment_type,
            description=description,
            language=language,
            salary_min=salary.min if salary else None,
            salary_max=salary.max if salary else None,
            salary_currency=salary.currency if salary else rules.salary.default_currency,
            salary_period=salary.period if salary else None,
            published_at=parse_datetime(raw.posted_at_text, rules.timezone, "start"),
            deadline_at=parse_datetime(raw.deadline_text, rules.timezone, "end"),
            scraped_at=scraped_at or datetime.now(timezone.utc),
            raw_data=raw.model_dump(mode="json", exclude={"description"}),
        )
    except ValidationError as exc:
        reason = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        raise NormalizationError(raw, reason) from exc
