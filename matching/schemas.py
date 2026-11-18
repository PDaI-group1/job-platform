from typing import Literal

from pydantic import BaseModel, Field

Seniority = Literal["junior", "mid", "senior", "lead"]


class JobRequirements(BaseModel):
    must_have_skills: list[str] = Field(
        description="Skills and qualifications explicitly required for the role"
    )
    nice_to_have_skills: list[str] = Field(
        description="Skills mentioned as a plus, beneficial, or preferred but not required"
    )
    seniority: Seniority | None = Field(
        None,
        description="Seniority level of the role; null if not stated or unclear",
    )
    required_languages: list[str] = Field(
        description="Human languages required or expected (e.g. Finnish, English, Swedish)"
    )
