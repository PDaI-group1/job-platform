from pydantic import BaseModel, Field


class Experience(BaseModel):
    title: str = Field(description="Job title or role")
    years: float | None = Field(None, description="Years in this role; null if not stated")


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
    languages: list[str] = Field(
        description="Human languages the candidate speaks or mentions"
    )


class CVProfile(CVExtraction):
    """CVExtraction enriched with ESCO normalisation results."""

    skill_matches: list[SkillMatch] = Field(
        description="Skills with ESCO normalisation results",
        default_factory=list,
    )
