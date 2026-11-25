from typing import Literal

from pydantic import BaseModel, Field

Seniority = Literal["junior", "mid", "senior", "lead", "intern"]


class LanguageRequirement(BaseModel):
    code: str = Field(description="ISO 639-1 language code, e.g. 'fi', 'en', 'sv'")
    requirement: Literal["required", "advantage"] = Field(
        description="'required' if the ad states it is mandatory, 'advantage' if mentioned as a plus"
    )


class JobRequirements(BaseModel):
    must_have_skills: list[list[str]] = Field(
        description=(
            "Required skills. Each inner list is a set of acceptable alternatives for one requirement. "
            "E.g. 'Java, TypeScript or Python' -> [['Java', 'TypeScript', 'Python']]. "
            "Single-skill requirements are wrapped in a list: [['Python']]."
        )
    )
    nice_to_have_skills: list[list[str]] = Field(
        description="Preferred skills; same format as must_have_skills."
    )
    seniority: Seniority | None = Field(
        None,
        description="Seniority level of the role; null if not stated or unclear",
    )
    required_languages: list[LanguageRequirement] = Field(
        description=(
            "Human languages required or expected. Use ISO 639-1 codes "
            "(e.g. 'fi' for Finnish, 'en' for English, 'sv' for Swedish)."
        )
    )
