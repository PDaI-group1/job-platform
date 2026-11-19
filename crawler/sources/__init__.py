from crawler.core.base import BaseSource
from crawler.sources.jobly import JoblySource

SOURCES: dict[str, type[BaseSource]] = {
    JoblySource.name: JoblySource,
}


def get_source_class(name: str) -> type[BaseSource]:
    try:
        return SOURCES[name]
    except KeyError:
        raise KeyError(f"unknown source {name!r}; available: {', '.join(sorted(SOURCES))}") from None
