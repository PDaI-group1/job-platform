import html
import re
import unicodedata

_SPACES = re.compile(r"[ \t\u00a0\u2000-\u200b\u202f\u205f\u3000]+")
_ZERO_WIDTH = re.compile(r"[\u200b-\u200d\ufeff]")
_POSTAL_CODE = re.compile(r"\b\d{5}\b")


def _base(value: str) -> str:
    value = html.unescape(value)
    value = unicodedata.normalize("NFC", value)
    return _ZERO_WIDTH.sub("", value)


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = _SPACES.sub(" ", _base(value).replace("\n", " ").replace("\r", " ")).strip()
    return value or None


def clean_multiline(value: str | None, max_length: int | None = None) -> str | None:
    if value is None:
        return None
    value = _base(value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [_SPACES.sub(" ", line).strip() for line in value.split("\n")]
    value = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    if max_length and len(value) > max_length:
        value = value[:max_length].rstrip() + "…"
    return value or None


def clean_company(value: str | None) -> str | None:
    value = clean_text(value)
    if value is None:
        return None
    return value.strip(" ,;-–") or None


def clean_location(value: str | None) -> str | None:
    value = clean_text(value)
    if value is None:
        return None
    parts: dict[str, None] = {}
    for part in re.split(r"[,;/]", value):
        part = _POSTAL_CODE.sub("", part).strip(" -–")
        part = re.sub(r"\s{2,}", " ", part)
        if part and part.lower() not in {p.lower() for p in parts}:
            parts[part] = None
    return ", ".join(parts) or None
