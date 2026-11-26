from __future__ import annotations

import html
import json
from typing import Any

from crawler.config import Employer, normalize_label
from crawler.core.base import ParseError
from crawler.core.html import element_to_text, make_soup
from crawler.schemas import RawJob

SOURCE = "greenhouse"

_EMPLOYMENT_LABELS = {"employment type", "employment", "type of employment", "contract type", "job type", "työsuhde"}
_WORK_MODE_LABELS = {"workplace type", "work mode", "remote", "remote type", "location type", "remote status"}


def parse_jobs(text: str, employer: Employer) -> list[RawJob]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Greenhouse feed is not JSON: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise ParseError("Greenhouse feed has no 'jobs' list")
    return [job for item in data["jobs"] if (job := parse_job(item, employer)) is not None]


def parse_job(item: Any, employer: Employer) -> RawJob | None:
    if not isinstance(item, dict) or item.get("id") is None or not item.get("absolute_url"):
        return None

    metadata = _metadata(item.get("metadata"))
    description, embedded = _description(item.get("content"))
    offices = [o for o in item.get("offices") or [] if isinstance(o, dict)]
    office_locations = [str(o.get("location") or o.get("name") or "") for o in offices]
    departments = [d.get("name") for d in item.get("departments") or [] if isinstance(d, dict) and d.get("name")]

    extra: dict[str, Any] = {
        "board_token": employer.token,
        "offices": [x for x in office_locations if x],
        "departments": departments,
    }
    if item.get("company_name"):
        extra["feed_company_name"] = item["company_name"]
    if metadata:
        extra["metadata"] = metadata
    if embedded:
        extra["embedded"] = {k: v for k, v in embedded.items() if k not in {"image", "intro"}}
        if countries := _str_list(embedded.get("country")):
            extra["countries"] = countries
    if not item.get("first_published"):
        extra["posted_at_from"] = "updated_at"

    return RawJob(
        source=SOURCE,
        source_job_id=str(item["id"]),
        url=item["absolute_url"],
        title=item.get("title"),
        company=employer.name or item.get("company_name"),
        location=(item.get("location") or {}).get("name") if isinstance(item.get("location"), dict) else None,
        description=description,
        posted_at_text=item.get("first_published") or item.get("updated_at"),
        employment_type_text=_first(metadata, _EMPLOYMENT_LABELS),
        work_mode_text=_first(metadata, _WORK_MODE_LABELS),
        language_hint=_str(embedded.get("lang")) or item.get("language"),
        detail_fetched=True,
        extra=extra,
    )


def location_texts(job: RawJob) -> list[str]:
    return [t for t in [job.location, *job.extra.get("offices", []), *job.extra.get("countries", [])] if t]


def _description(content: Any) -> tuple[str | None, dict[str, Any]]:
    if not isinstance(content, str) or not content.strip():
        return None, {}
    text = element_to_text(make_soup(html.unescape(content)))
    text, embedded = split_embedded_json(text)
    intro = _str(embedded.get("intro"))
    if intro and intro not in text:
        text = f"{intro}\n\n{text}" if text else intro
    return text or None, embedded


def split_embedded_json(text: str) -> tuple[str, dict[str, Any]]:
    stripped = text.lstrip()
    if not stripped.startswith("{"):
        return text, {}
    try:
        obj, end = json.JSONDecoder().raw_decode(stripped)
    except json.JSONDecodeError:
        return text, {}
    if not isinstance(obj, dict):
        return text, {}
    return stripped[end:].lstrip(), obj


def _str(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _str_list(value: Any) -> list[str]:
    values = value if isinstance(value, list) else [value]
    return [v.strip() for v in values if isinstance(v, str) and v.strip()]


def _metadata(raw: Any) -> dict[str, str]:
    out: dict[str, str] = {}
    for entry in raw or []:
        if not isinstance(entry, dict) or not entry.get("name"):
            continue
        value = entry.get("value")
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value if v)
        if value not in (None, "", []):
            out[normalize_label(str(entry["name"]))] = str(value)
    return out


def _first(metadata: dict[str, str], labels: set[str]) -> str | None:
    return next((v for k, v in metadata.items() if k in labels), None)
