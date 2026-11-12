import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin

from bs4 import Tag

from crawler.config import SourceConfig
from crawler.core.base import ParseError
from crawler.core.html import (
    element_to_text,
    extract_json_ld,
    extract_labeled_fields,
    make_soup,
    select_text,
    strip_patterns,
    text_of,
)
from crawler.schemas import RawJob

log = logging.getLogger(__name__)


@dataclass
class ListingPage:
    jobs: list[RawJob] = field(default_factory=list)
    has_next: bool = False
    skipped: int = 0


def parse_listing(html: str, config: SourceConfig, page_url: str) -> ListingPage:
    soup = make_soup(html, config.html_parser)
    sel = config.listing.selectors
    page = ListingPage(has_next=bool(sel.get("next_page") and soup.select_one(sel["next_page"])))

    items = soup.select(sel["item"])
    if any(item.select_one(sel["item"]) for item in items):
        raise ParseError(f"job cards are nested on {page_url}: the HTML parser restructured the page "
                         f"(html_parser={config.html_parser!r}); try html5lib")
    for item in items:
        try:
            page.jobs.append(_parse_listing_item(item, config, page_url))
        except ParseError as exc:
            page.skipped += 1
            log.warning("skipping listing item on %s: %s", page_url, exc)
    return page


def _parse_listing_item(item: Tag, config: SourceConfig, page_url: str) -> RawJob:
    sel = config.listing.selectors
    link = item.select_one(sel["link"])
    if link is None or not link.get("href"):
        raise ParseError("no job link")
    url = urljoin(page_url, link["href"])
    job_id = _extract_id(item, url, config)
    if job_id is None:
        raise ParseError(f"cannot extract id from {url}")

    date_text = select_text(item, sel.get("date"))
    company = select_text(item, sel.get("company"))
    if not company:
        company = _company_from_meta(select_text(item, sel.get("meta")), date_text)

    classes = item.get("class") or []
    company_link = item.select_one(f'{sel["company"]} a[href]') if sel.get("company") else None
    extra: dict[str, Any] = {"featured": "highlighted-job" in classes}
    if company_link is not None:
        extra["company_profile_url"] = urljoin(page_url, company_link["href"])

    return RawJob(
        source=config.name,
        source_job_id=job_id,
        url=url,
        title=link.get("title") or text_of(link),
        company=company,
        location=select_text(item, sel.get("location")),
        posted_at_text=date_text.rstrip(", ") if date_text else None,
        salary_text=select_text(item, sel.get("salary")),
        extra=extra,
    )


def _extract_id(item: Tag, url: str, config: SourceConfig) -> str | None:
    for pattern in config.listing.id_patterns:
        value = url if pattern.attr == "href" else item.get(pattern.attr)
        if isinstance(value, str) and (m := re.search(pattern.regex, value)):
            return m.group(1)
    return None


def _company_from_meta(meta: str | None, date_text: str | None) -> str | None:
    if not meta:
        return None
    if date_text and meta.startswith(date_text):
        meta = meta[len(date_text):]
    meta = re.sub(r"^\s*\d{1,2}\.\d{1,2}\.\d{2,4}\s*,?", "", meta)
    return meta.strip(" ,") or None


def parse_detail(html: str, config: SourceConfig, job: RawJob) -> RawJob:
    soup = make_soup(html, config.html_parser)
    sel = config.detail.selectors
    json_ld = extract_json_ld(soup) if config.detail.use_json_ld else None
    body = soup.select_one(sel["body"])
    if body is None and json_ld is None:
        raise ParseError(f"no description body ({sel['body']}) and no JSON-LD on {job.url}")

    data: dict[str, Any] = {}
    extra: dict[str, Any] = {}

    if json_ld:
        data.update(_from_json_ld(json_ld, config.html_parser))
        extra["json_ld"] = True
        for key, extra_key in (("skills", "json_ld_skills"), ("occupationalCategory", "occupational_category")):
            if isinstance(json_ld.get(key), str) and json_ld[key].strip():
                extra[extra_key] = json_ld[key].strip()

    if body is not None:
        text = strip_patterns(element_to_text(body), config.detail.strip_patterns)
        known, unknown = extract_labeled_fields(text, config.detail.label_index())
        data["description"] = text
        _apply_labeled_fields(known, data, extra)
        if unknown:
            extra["unmapped_labels"] = unknown

    return RawJob(
        source=job.source,
        source_job_id=job.source_job_id,
        url=job.url,
        title=select_text(soup, sel.get("title")) or data.pop("title", None),
        detail_fetched=True,
        extra=extra,
        **{k: v for k, v in data.items() if k != "title"},
    )


def _apply_labeled_fields(known: dict[str, str], data: dict[str, Any], extra: dict[str, Any]) -> None:
    if "deadline" in known:
        data["deadline_text"] = known["deadline"]
    if "salary" in known:
        data["salary_text"] = known["salary"]
    if "salary_period" in known:
        data["salary_period_text"] = known["salary_period"]
    employment = "; ".join(known[k] for k in ("employment_type", "work_time") if k in known)
    if employment:
        data["employment_type_text"] = employment
    if "work_mode" in known:
        data["work_mode_text"] = known["work_mode"]
    for key in ("address", "start_date", "reference", "education", "experience", "language_skills",
                "application_start", "duration", "work_location"):
        if key in known:
            extra[key] = known[key]


def _from_json_ld(obj: dict[str, Any], html_parser: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(obj.get("title"), str):
        out["title"] = obj["title"]
    if isinstance(obj.get("datePosted"), str):
        out["posted_at_text"] = obj["datePosted"]
    if isinstance(obj.get("validThrough"), str):
        out["deadline_text"] = obj["validThrough"]

    employment = obj.get("employmentType")
    values = employment if isinstance(employment, list) else [employment]
    meaningful = [v for v in values if isinstance(v, str) and v.strip() and v.strip().upper() != "OTHER"]
    if meaningful:
        out["employment_type_text"] = meaningful[0]
    if isinstance(obj.get("jobLocationType"), str):
        out["work_mode_text"] = obj["jobLocationType"]

    org = obj.get("hiringOrganization")
    if isinstance(org, dict) and isinstance(org.get("name"), str):
        out["company"] = org["name"]
    if isinstance(obj.get("inLanguage"), str):
        out["language_hint"] = obj["inLanguage"]
    if (salary := _salary_from_json_ld(obj.get("baseSalary"))) is not None:
        out["salary_text"] = salary
    if isinstance(obj.get("description"), str):
        out["description"] = element_to_text(make_soup(obj["description"], html_parser))
    return out


def _salary_from_json_ld(base: Any) -> str | None:
    if not isinstance(base, dict):
        return None

    def present(v: Any) -> bool:
        return v is not None and str(v).strip() != ""

    value = base.get("value")
    currency = base.get("currency") or "EUR"
    if isinstance(value, dict):
        lo, hi, single = value.get("minValue"), value.get("maxValue"), value.get("value")
        unit = value.get("unitText") or ""
    else:
        lo = hi = None
        single, unit = value, base.get("unitText") or ""
    if present(lo) and present(hi):
        amount = f"{lo}-{hi}"
    elif present(single) or present(lo) or present(hi):
        amount = str(next(v for v in (single, lo, hi) if present(v)))
    else:
        return None
    return f"{amount} {currency} / {unit}".strip(" /")
