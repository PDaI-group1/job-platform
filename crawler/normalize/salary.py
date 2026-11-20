import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from crawler.config import SalaryRules

_NUM = r"\d{1,3}(?:[ \u00a0\u202f.]\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?"
_CUR = r"(?:€|eur(?:oa?)?\b|euro\w*)"
_DASH = r"\s*(?:-|–|—|to|\.\.\.?)\s*"

_RANGE_AFTER = re.compile(rf"(?P<a>{_NUM})\s*{_CUR}?{_DASH}(?P<b>{_NUM})\s*{_CUR}", re.IGNORECASE)
_RANGE_BEFORE = re.compile(rf"{_CUR}\s*(?P<a>{_NUM}){_DASH}{_CUR}?\s*(?P<b>{_NUM})", re.IGNORECASE)
_SINGLE = re.compile(rf"(?:{_CUR}\s*(?P<a>{_NUM}))|(?:(?P<b>{_NUM})\s*{_CUR})", re.IGNORECASE)
_UPPER = re.compile(r"(<|≤|\balle\b|\bmax\.?|\benintään\b|\bup\s+to\b|\bkorkeintaan\b)", re.IGNORECASE)
_LOWER = re.compile(r"(>|≥|\byli\b|\balkaen\b|\bvähintään\b|\bfrom\b|\bmin\.?|\bstarting\b)", re.IGNORECASE)


@dataclass(frozen=True)
class Salary:
    min: Decimal | None
    max: Decimal | None
    currency: str
    period: str | None


def _to_decimal(raw: str) -> Decimal | None:
    s = raw.replace("\u00a0", " ").replace("\u202f", " ")
    if re.fullmatch(r"\d{1,3}(?:[ .]\d{3})+(?:,\d{1,2})?", s):
        s = s.replace(" ", "").replace(".", "").replace(",", ".")
    else:
        s = s.replace(" ", "").replace(",", ".")
    try:
        value = Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None
    return value if value > 0 else None


def detect_period(text: str, rules: SalaryRules) -> str | None:
    for period, patterns in rules.periods.items():
        if any(re.search(p, text, re.IGNORECASE) for p in patterns):
            return period
    return None


def parse_salary(text: str | None, rules: SalaryRules, period_hint: str | None = None) -> Salary | None:
    if not text:
        return None

    lo = hi = None
    if m := (_RANGE_AFTER.search(text) or _RANGE_BEFORE.search(text)):
        lo, hi = _to_decimal(m["a"]), _to_decimal(m["b"])
        prefix = text[: m.start()]
    elif m := _SINGLE.search(text):
        value = _to_decimal(m["a"] or m["b"])
        prefix = text[: m.start()]
        if _UPPER.search(prefix[-15:]):
            hi = value
        elif _LOWER.search(prefix[-15:]):
            lo = value
        else:
            lo = hi = value
    else:
        return None

    if lo is None and hi is None:
        return None
    if lo is not None and hi is not None and lo > hi:
        lo, hi = hi, lo

    period = detect_period(text, rules) or (detect_period(period_hint, rules) if period_hint else None)
    if period is None:
        ref = hi or lo
        h = rules.heuristic
        period = "hour" if ref < Decimal(str(h.hour_below)) else "year" if ref > Decimal(str(h.year_above)) else "month"

    return Salary(min=lo, max=hi, currency=rules.default_currency, period=period)
