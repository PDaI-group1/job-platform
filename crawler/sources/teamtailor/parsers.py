from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

from crawler.config import Employer
from crawler.core.base import ParseError
from crawler.core.html import element_to_text, make_soup
from crawler.schemas import RawJob

SOURCE = "teamtailor"

_REMOTE_STATUS = {"fully": "remote", "remote": "remote", "hybrid": "hybrid", "none": "onsite"}
_JOB_ID = re.compile(r"/jobs/(\d+)")


def parse_feed(text: str, employer: Employer) -> list[RawJob]:
    try:
        root = ET.fromstring(text.lstrip("﻿").encode("utf-8"))
    except ET.ParseError as exc:
        raise ParseError(f"Teamtailor feed is not valid XML: {exc}") from exc
    if _local(root.tag) != "rss":
        raise ParseError(f"Teamtailor feed root is <{_local(root.tag)}>, expected <rss>")
    return [job for item in root.iter() if _local(item.tag) == "item" if (job := parse_item(item, employer))]


def parse_item(item: ET.Element, employer: Employer) -> RawJob | None:
    link = _text(item, "link")
    if not link:
        return None
    m = _JOB_ID.search(link)
    job_id = m.group(1) if m else _text(item, "guid")
    if not job_id:
        return None

    locations = _locations(item)
    cities = _unique(loc.get("city") or loc.get("name") for loc in locations)
    remote_status = (_text(item, "remoteStatus") or _text(item, "remote_status") or "").strip().lower()

    extra: dict[str, Any] = {
        "career_site": employer.url,
        "locations": locations,
        "department": _text(item, "department"),
        "role": _text(item, "role"),
        "division": _text(item, "division"),
        "remote_status": remote_status or None,
        "guid": _text(item, "guid"),
    }
    description = _text(item, "description")
    return RawJob(
        source=SOURCE,
        source_job_id=job_id,
        url=link,
        title=_text(item, "title"),
        company=employer.name or None,
        location=", ".join(cities) or None,
        description=element_to_text(make_soup(description)) if description else None,
        posted_at_text=_text(item, "pubDate"),
        work_mode_text=_REMOTE_STATUS.get(remote_status),
        detail_fetched=True,
        extra={k: v for k, v in extra.items() if v not in (None, "", [])},
    )


def location_texts(job: RawJob) -> list[str]:
    texts = [job.location or ""]
    for loc in job.extra.get("locations", []):
        texts += [v for v in loc.values() if v]
    return [t for t in texts if t]


def _locations(item: ET.Element) -> list[dict[str, str]]:
    out = []
    for el in item.iter():
        if _local(el.tag) != "location":
            continue
        fields = {_local(child.tag): (child.text or "").strip() for child in el}
        fields = {k: v for k, v in fields.items() if k in {"name", "city", "country", "zip", "address"} and v}
        if not fields and (el.text or "").strip():
            fields = {"name": el.text.strip()}
        if fields:
            out.append(fields)
    return out


def _text(item: ET.Element, name: str) -> str | None:
    for child in item:
        if _local(child.tag) == name:
            return (child.text or "").strip() or None
    return None


def _local(tag: Any) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _unique(values) -> list[str]:
    seen: dict[str, None] = {}
    for v in values:
        if v and v.lower() not in {s.lower() for s in seen}:
            seen[v] = None
    return list(seen)
