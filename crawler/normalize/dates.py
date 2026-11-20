import re
from datetime import date, datetime, time, timezone
from typing import Literal
from zoneinfo import ZoneInfo

_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?\s*(Z|[+-]\d{2}:?\d{2})?)?")
_EU = re.compile(
    r"\b(\d{1,2})\.(\d{1,2})\.(\d{4}|\d{2})\b"
    r"(?:\s*(?:klo|kello|kl\.?|at|,)?\s*(\d{1,2})[:.](\d{2}))?",
    re.IGNORECASE,
)

Kind = Literal["start", "end"]


def parse_datetime(value: str | None, tz: str = "Europe/Helsinki", kind: Kind = "start") -> datetime | None:
    if not value:
        return None
    local = ZoneInfo(tz)
    try:
        if m := _ISO.search(value):
            y, mo, d, hh, mm, ss, offset = m.groups()
            day = date(int(y), int(mo), int(d))
            if hh is None:
                return _date_only(day, local, kind)
            dt = datetime.combine(day, time(int(hh), int(mm), int(ss or 0)))
            if offset:
                offset = "+00:00" if offset == "Z" else offset
                if ":" not in offset:
                    offset = f"{offset[:3]}:{offset[3:]}"
                return datetime.fromisoformat(dt.isoformat() + offset).astimezone(timezone.utc)
            return dt.replace(tzinfo=local).astimezone(timezone.utc)

        if m := _EU.search(value):
            d, mo, y, hh, mm = m.groups()
            year = int(y) + 2000 if len(y) == 2 else int(y)
            day = date(year, int(mo), int(d))
            if hh is None:
                return _date_only(day, local, kind)
            return datetime.combine(day, time(int(hh), int(mm))).replace(tzinfo=local).astimezone(timezone.utc)
    except ValueError:
        return None
    return None


def _date_only(day: date, tz: ZoneInfo, kind: Kind) -> datetime:
    t = time(23, 59, 59) if kind == "end" else time(0, 0)
    return datetime.combine(day, t).replace(tzinfo=tz).astimezone(timezone.utc)
