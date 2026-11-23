from __future__ import annotations

from crawler.core.base import BaseSource
from crawler.sources.greenhouse import GreenhouseSource
from crawler.sources.jobly import JoblySource
from crawler.sources.lever import LeverSource
from crawler.sources.teamtailor import TeamtailorSource

SOURCES: dict[str, type[BaseSource]] = {
    cls.name: cls for cls in (JoblySource, GreenhouseSource, LeverSource, TeamtailorSource)
}

GROUPS: dict[str, list[str]] = {
    "feeds": ["greenhouse", "lever", "teamtailor"],
    "all": list(SOURCES),
}


def get_source_class(name: str) -> type[BaseSource]:
    try:
        return SOURCES[name]
    except KeyError:
        raise KeyError(f"unknown source {name!r}; available: {', '.join(sorted(SOURCES))}") from None


def expand_sources(names: list[str]) -> list[str]:
    out: list[str] = []
    for name in names:
        for source in GROUPS.get(name, [name]):
            if source not in out:
                out.append(source)
    return out
