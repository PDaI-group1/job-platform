import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

RemoteType = Literal["onsite", "hybrid", "remote"]
EmploymentType = Literal["full_time", "part_time", "internship", "temporary", "contract"]
SalaryPeriod = Literal["hour", "month", "year"]
Language = Literal["fi", "en", "sv"]

HASHED_FIELDS = (
    "url", "title", "company_name", "location", "remote_type", "employment_type", "description",
    "skills", "language", "salary_min", "salary_max", "salary_currency", "salary_period",
    "published_at", "deadline_at",
)


class JobRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str = Field(min_length=1, max_length=50)
    source_job_id: str = Field(min_length=1, max_length=200)
    url: str = Field(pattern=r"^https?://")
    title: str = Field(min_length=1, max_length=500)
    company_name: str | None = Field(None, max_length=300)
    location: str | None = Field(None, max_length=500)
    remote_type: RemoteType | None = None
    employment_type: EmploymentType | None = None
    description: str | None = None
    skills: list[str] = Field(default_factory=list)
    language: Language | None = None
    salary_min: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    salary_max: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    salary_currency: str = Field("EUR", pattern=r"^[A-Z]{3}$")
    salary_period: SalaryPeriod | None = None
    published_at: AwareDatetime | None = None
    deadline_at: AwareDatetime | None = None
    is_active: bool = True
    scraped_at: AwareDatetime
    raw_data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("skills")
    @classmethod
    def _skills(cls, v: list[str]) -> list[str]:
        seen: dict[str, None] = {}
        for s in v:
            s = s.strip().lower()
            if s:
                seen.setdefault(s, None)
        return list(seen)

    @model_validator(mode="after")
    def _salary_range(self) -> JobRecord:
        if self.salary_min is not None and self.salary_max is not None and self.salary_min > self.salary_max:
            raise ValueError(f"salary_min {self.salary_min} > salary_max {self.salary_max}")
        return self

    @property
    def content_hash(self) -> str:
        payload = {f: getattr(self, f) for f in HASHED_FIELDS}
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=_json_default)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def to_db_row(self) -> dict[str, Any]:
        row = self.model_dump()
        row["content_hash"] = self.content_hash
        return row

    def to_json_dict(self) -> dict[str, Any]:
        row = self.model_dump(mode="json")
        row["content_hash"] = self.content_hash
        return row


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value.normalize())
    raise TypeError(f"not JSON serializable: {type(value)}")
