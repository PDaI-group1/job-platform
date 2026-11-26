from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from crawler.config import Employer
from crawler.core.base import ParseError
from crawler.core.html import element_to_text, make_soup
from crawler.schemas import RawJob

SOURCE = "lever"

_INTERVALS = {
    "per-year-salary": "year", "per-month-salary": "month", "per-hour-wage": "hour",
    "per-week-salary": "week", "per-day-wage": "day", "one-time": "one-time",
}


def parse_postings(text: str, employer: Employer) -> list[RawJob]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Lever feed is not JSON: {exc}") from exc
    if not isinstance(data, list):
        raise ParseError("Lever feed is not a list of postings")
    return [job for item in data if (job := parse_posting(item, employer)) is not None]


def parse_posting(item: Any, employer: Employer) -> RawJob | None:
    if not isinstance(item, dict) or not item.get("id") or not item.get("hostedUrl"):
        return None
    categories = item.get("categories") if isinstance(item.get("categories"), dict) else {}
    all_locations = [str(x) for x in categories.get("allLocations") or [] if x]
    location = categories.get("location") or (", ".join(all_locations) or None)

    salary_text, salary_extra = _salary(item.get("salaryRange"))
    extra: dict[str, Any] = {
        "site": employer.token,
        "country": item.get("country"),
        "all_locations": all_locations,
        "team": categories.get("team"),
        "department": categories.get("department"),
        "apply_url": item.get("applyUrl"),
    }
    if salary_extra:
        extra["salary_range"] = salary_extra
    if item.get("salaryDescriptionPlain") or item.get("salaryDescription"):
        extra["salary_description"] = item.get("salaryDescriptionPlain") or item.get("salaryDescription")

    workplace = item.get("workplaceType")
    return RawJob(
        source=SOURCE,
        source_job_id=str(item["id"]),
        url=item["hostedUrl"],
        title=item.get("text"),
        company=employer.name or None,
        location=location,
        description=_description(item),
        posted_at_text=_millis_to_iso(item.get("createdAt")),
        salary_text=salary_text,
        employment_type_text=categories.get("commitment"),
        work_mode_text=workplace if workplace and workplace != "unspecified" else None,
        detail_fetched=True,
        extra={k: v for k, v in extra.items() if v not in (None, "", [])},
    )


def location_texts(job: RawJob) -> list[str]:
    return [t for t in [job.location, job.extra.get("country"), *job.extra.get("all_locations", [])] if t]


def _description(item: dict[str, Any]) -> str | None:
    parts: list[str] = []
    main = item.get("descriptionPlain") or _html(item.get("description"))
    if main:
        parts.append(main.strip())
    for block in item.get("lists") or []:
        if not isinstance(block, dict):
            continue
        heading = (block.get("text") or "").strip()
        body = _html(f"<ul>{block.get('content') or ''}</ul>")
        if heading or body:
            parts.append("\n\n".join(p for p in (heading, body) if p))
    closing = item.get("additionalPlain") or _html(item.get("additional"))
    if closing:
        parts.append(closing.strip())
    return "\n\n".join(parts) or None


def _html(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return element_to_text(make_soup(value)) or None


def _millis_to_iso(value: Any) -> str | None:
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()


def _salary(raw: Any) -> tuple[str | None, dict[str, Any] | None]:
    if not isinstance(raw, dict) or (raw.get("min") is None and raw.get("max") is None):
        return None, None
    currency = str(raw.get("currency") or "").upper()
    if currency != "EUR":
        return None, raw
    lo, hi = raw.get("min"), raw.get("max")
    amount = f"{lo}-{hi}" if lo is not None and hi is not None else str(lo if lo is not None else hi)
    if lo is None:
        amount = f"max {amount}"
    elif hi is None:
        amount = f"from {amount}"
    period = _INTERVALS.get(str(raw.get("interval") or ""), "")
    return f"{amount} EUR / {period}".strip(" /"), raw
