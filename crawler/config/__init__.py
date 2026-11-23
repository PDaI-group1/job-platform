import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class SourceConfig(_Strict):
    name: str
    display_name: str
    base_url: str
    fetcher: Literal["http", "playwright"] = "http"
    html_parser: Literal["html5lib", "html.parser", "lxml"] = "html5lib"
    http: HttpConfig
    listing: ListingConfig
    detail: DetailConfig


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


class NormalizationRules(_Strict):
    timezone: str = "Europe/Helsinki"
    max_description_length: int = 50000
    negation: NegationRules = NegationRules()
    remote_type: dict[Literal["onsite", "hybrid", "remote"], list[str]]
    employment_type: dict[Literal["full_time", "part_time", "internship", "temporary", "contract"], list[str]]
    language: LanguageRules
    salary: SalaryRules

    @field_validator("remote_type", "employment_type")
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
