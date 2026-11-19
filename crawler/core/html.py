import copy
import json
import logging
import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from crawler.config import normalize_label
from crawler.normalize.text import clean_text

log = logging.getLogger(__name__)

_BLOCK_TAGS = [
    "p", "div", "section", "article", "header", "footer", "center", "blockquote", "pre",
    "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "table", "tr", "hr",
]
_DROP_TAGS = ["script", "style", "noscript", "template", "iframe", "svg", "button", "form"]
_DROP_SELECTORS = "[data-cfemail], a.__cf_email__, a[href*='/cdn-cgi/l/email-protection']"
_CF_EMAIL_TEXT = re.compile(r"\[email(?:\s|&#160;|\u00a0)*protected\]", re.IGNORECASE)

_LABEL_LINE = re.compile(r"^(?:[-•*]\s*)?(?P<label>[^\W\d_][^:.!?\n]{0,48}?)\s*:\s*(?P<value>.*)$")


def make_soup(html: str, parser: str = "html5lib") -> BeautifulSoup:
    return BeautifulSoup(html, parser)


def text_of(element: Tag | None) -> str | None:
    if element is None:
        return None
    return clean_text(element.get_text(" "))


def select_text(root: Tag, selector: str | None) -> str | None:
    if not selector:
        return None
    return text_of(root.select_one(selector))


def element_to_text(element: Tag) -> str:
    el = copy.copy(element)
    for tag in el.find_all(_DROP_TAGS):
        tag.decompose()
    for tag in el.select(_DROP_SELECTORS):
        tag.decompose()
    for br in el.find_all("br"):
        br.replace_with("\n")
    for li in reversed(el.find_all("li")):
        inner = re.sub(r"\s+", " ", li.get_text(" ")).strip()
        li.clear()
        li.append(f"\n- {inner}\n" if inner else "")
    for tag in el.find_all(_BLOCK_TAGS):
        tag.insert_before("\n\n")
        tag.insert_after("\n\n")
    text = _CF_EMAIL_TEXT.sub("", el.get_text(""))
    lines = [re.sub(r"[ \t\u00a0]+", " ", line).strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def extract_labeled_fields(text: str, label_index: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    known: dict[str, str] = {}
    unknown: dict[str, str] = {}
    lines = [line.strip() for line in text.split("\n")]
    for i, line in enumerate(lines):
        m = _LABEL_LINE.match(line)
        if not m or len(m["label"].split()) > 6:
            continue
        value = m["value"].strip()
        if not value:
            value = next((nxt for nxt in lines[i + 1: i + 3] if nxt), "")
            if _LABEL_LINE.match(value) or value.startswith("- "):
                continue
        if not value:
            continue
        label = normalize_label(m["label"])
        key = label_index.get(label)
        if key:
            known.setdefault(key, value)
        elif len(unknown) < 30:
            unknown.setdefault(label, value[:300])
    return known, unknown


def strip_patterns(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
    return text


def extract_json_ld(soup: BeautifulSoup, wanted_type: str = "JobPosting") -> dict[str, Any] | None:
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text()
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            log.debug("skipping invalid JSON-LD block")
            continue
        for obj in _walk_json_ld(data):
            types = obj.get("@type")
            types = types if isinstance(types, list) else [types]
            if wanted_type in types:
                return obj
    return None


def _walk_json_ld(data: Any):
    if isinstance(data, list):
        for item in data:
            yield from _walk_json_ld(item)
    elif isinstance(data, dict):
        yield data
        if "@graph" in data:
            yield from _walk_json_ld(data["@graph"])
