from typing import Literal

from pydantic import BaseModel, Field


class SkillResult(BaseModel):
    skill: list[str] = Field(description="The requirement as a list of acceptable alternatives")
    status: Literal["matched", "partial", "missing"] = Field(
        description="matched: similarity >= MATCH_THRESHOLD or exact; partial: >= PARTIAL_THRESHOLD; missing: below"
    )
    matched_by: str | None = Field(
        None, description="CV skill (label if available, else raw) that best matched this requirement"
    )
    score: float = Field(description="Best cosine similarity found (0–1); 1.0 for exact matches")


class LanguageResult(BaseModel):
    code: str = Field(description="ISO 639-1 language code")
    requirement: Literal["required", "advantage"]
    cv_level: Literal["native", "fluent", "good", "basic"] | None = Field(
        None,
        description="Proficiency level from the CV; null if the candidate does not list this language",
    )


class MatchResult(BaseModel):
    score: float = Field(description="Overall match score 0–100, based on skills only (languages excluded)")
    must_have: list[SkillResult]
    nice_to_have: list[SkillResult]
    languages: list[LanguageResult]
