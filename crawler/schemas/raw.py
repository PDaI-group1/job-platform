from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RawJob(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source: str = Field(min_length=1)
    source_job_id: str = Field(min_length=1)
    url: str = Field(min_length=1)

    title: str | None = None
    company: str | None = None
    location: str | None = None
    description: str | None = None

    posted_at_text: str | None = None
    deadline_text: str | None = None
    salary_text: str | None = None
    salary_period_text: str | None = None
    employment_type_text: str | None = None
    work_mode_text: str | None = None
    language_hint: str | None = None

    detail_fetched: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)

    @field_validator("*", mode="before")
    @classmethod
    def _empty_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    def merged(self, other: RawJob) -> RawJob:
        data = self.model_dump()
        for key, value in other.model_dump(exclude={"extra"}).items():
            if value not in (None, "", False):
                data[key] = value
        data["extra"] = {**self.extra, **other.extra}
        return RawJob.model_validate(data)
