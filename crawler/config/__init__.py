from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CONFIG_DIR = Path(__file__).resolve().parent
SOURCES_DIR = CONFIG_DIR / "sources"
NORMALIZATION_FILE = CONFIG_DIR / "normalization.yml"


class ConfigError(Exception):
    """Config file is missing or invalid."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _check_regexes(patterns: list[str]) -> list[str]:
    for p in patterns:
        try:
            re.compile(p)
        except re.error as exc:
            raise ValueError(f"invalid regex {p!r}: {exc}") from exc
    return patterns


class HttpConfig(_Strict):
    user_agent: str
    timeout_seconds: float = Field(20, gt=0)
    delay_seconds: float = Field(1.0, ge=0)
    jitter_seconds: float = Field(0.0, ge=0)
    max_retries: int = Field(3, ge=0, le=10)
    backoff_seconds: float = Field(2.0, ge=0)
    respect_robots_txt: bool = True
    accept: str = "text/html,application/xhtml+xml"


class IdPattern(_Strict):
    attr: str
    regex: str

    @field_validator("regex")
    @classmethod
    def _valid(cls, v: str) -> str:
        _check_regexes([v])
        if re.compile(v).groups < 1:
            raise ValueError("id regex must contain a capture group")
        return v


class ListingConfig(_Strict):
    start_url: str
    page_param: str = "page"
    first_page: int = 0
    selectors: dict[str, str]
    id_patterns: list[IdPattern] = []


class DetailConfig(_Strict):
    selectors: dict[str, str]
    use_json_ld: bool = True
    field_labels: dict[str, list[str]] = {}
    strip_patterns: list[str] = []

    @field_validator("strip_patterns")
    @classmethod
    def _valid(cls, v: list[str]) -> list[str]:
        return _check_regexes(v)

    def label_index(self) -> dict[str, str]:
        index: dict[str, str] = {}
        for key, labels in self.field_labels.items():
            for label in labels:
                index[normalize_label(label)] = key
        return index


class Employer(_Strict):
    name: str
    token: str | None = None
    url: str | None = None

    @model_validator(mode="after")
    def _one_of(self) -> Employer:
        if not (self.token or self.url):
            raise ValueError(f"employer {self.name!r} needs a token or a url")
        return self

    @property
    def key(self) -> str:
        if self.token:
            return self.token
        host = re.sub(r"^https?://", "", self.url or "").split("/")[0]
        return host.split(".")[0] if host.endswith(".teamtailor.com") else host.removeprefix("careers.").removeprefix("career.").split(".")[0]


class FeedConfig(_Strict):
    format: Literal["json", "rss"]
    urls: list[str] = Field(min_length=1)
    finland_only: bool = True
    skip_open_applications: bool = True


class SourceConfig(_Strict):
    name: str
    display_name: str
    base_url: str
    fetcher: Literal["http", "playwright"] = "http"
    html_parser: Literal["html5lib", "html.parser", "lxml"] = "html5lib"
    http: HttpConfig
    listing: ListingConfig | None = None
    detail: DetailConfig | None = None
    feed: FeedConfig | None = None
    employers: list[Employer] = []

    @model_validator(mode="after")
    def _kind(self) -> SourceConfig:
        if self.feed is None and (self.listing is None or self.detail is None):
            raise ValueError("a source needs either `feed` + `employers` or `listing` + `detail`")
        if self.feed is not None and not self.employers:
            raise ValueError("a feed source needs at least one entry in `employers`")
        keys = [e.key for e in self.employers]
        if len(keys) != len(set(keys)):
            raise ValueError(f"duplicate employers: {keys}")
        return self


class NegationRules(_Strict):
    window_chars: int = 25
    after_window_chars: int = 0
    words: list[str] = []


class LanguageRules(_Strict):
    min_hits: int = 3
    stopwords: dict[str, list[str]]


class SalaryHeuristic(_Strict):
    hour_below: float = 100
    year_above: float = 15000


class SalaryRules(_Strict):
    default_currency: str = "EUR"
    periods: dict[Literal["hour", "month", "year"], list[str]]
    heuristic: SalaryHeuristic = SalaryHeuristic()


class FeedFilters(_Strict):
    finland_pattern: str
    skip_title_patterns: list[str] = []

    @field_validator("finland_pattern")
    @classmethod
    def _valid_one(cls, v: str) -> str:
        _check_regexes([v])
        return v

    @field_validator("skip_title_patterns")
    @classmethod
    def _valid(cls, v: list[str]) -> list[str]:
        return _check_regexes(v)


class NormalizationRules(_Strict):
    timezone: str = "Europe/Helsinki"
    max_description_length: int = 50000
    negation: NegationRules = NegationRules()
    remote_type: dict[Literal["onsite", "hybrid", "remote"], list[str]]
    remote_type_description: dict[Literal["onsite", "hybrid", "remote"], list[str]]
    employment_type: dict[Literal["full_time", "part_time", "internship", "temporary", "contract"], list[str]]
    language: LanguageRules
    salary: SalaryRules
    feed_filters: FeedFilters

    @field_validator("remote_type", "remote_type_description", "employment_type")
    @classmethod
    def _valid(cls, v: dict[str, list[str]]) -> dict[str, list[str]]:
        for patterns in v.values():
            _check_regexes(patterns)
        return v


def normalize_label(label: str) -> str:
    return re.sub(r"\s+", " ", label).strip().rstrip(":").strip().lower()


def _read_yaml(path: Path) -> dict:
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a mapping at the top level")
    return data


def load_source_config(name: str, path: Path | None = None) -> SourceConfig:
    path = path or SOURCES_DIR / f"{name}.yml"
    try:
        return SourceConfig.model_validate(_read_yaml(path))
    except ValueError as exc:
        raise ConfigError(f"invalid source config {path}:\n{exc}") from exc


def load_normalization_rules(path: Path | None = None) -> NormalizationRules:
    path = path or NORMALIZATION_FILE
    try:
        return NormalizationRules.model_validate(_read_yaml(path))
    except ValueError as exc:
        raise ConfigError(f"invalid normalization rules {path}:\n{exc}") from exc
