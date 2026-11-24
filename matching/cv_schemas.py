from typing import Literal

from pydantic import BaseModel, Field


class Experience(BaseModel):
    title: str = Field(description="Job title or role")
    years: float | None = Field(None, description="Years in this role; null if not stated. Convert months to years (e.g. 3 months → 0.25)")


class Language(BaseModel):
    code: str = Field(description="ISO 639-1 language code, e.g. 'fi', 'en', 'sv'")
    level: Literal["native", "fluent", "good", "basic"] | None = Field(
        None, description="Proficiency level; null if not stated"
    )


class SkillMatch(BaseModel):
    raw: str = Field(description="Skill as extracted from the CV")
    esco_label: str | None = Field(None, description="Matched ESCO preferred label; null if no match above threshold")
    score: float = Field(description="Cosine similarity score (0–1)")


class CVExtraction(BaseModel):
    """What the LLM returns — no computed fields."""

    skills: list[str] = Field(
        description="Skills as mentioned in the CV, in their original wording"
    )
    experience: list[Experience] = Field(
        description="Work experience entries: job title and years"
    )
    education: list[str] = Field(
        description="Degrees, qualifications or fields of study"
    )
    languages: list[Language] = Field(
        description="Human languages the candidate speaks or mentions"
    )


class CVProfile(CVExtraction):
    """CVExtraction enriched with ESCO normalisation results."""

    skill_matches: list[SkillMatch] = Field(
        description="Skills with ESCO normalisation results",
        default_factory=list,
    )
