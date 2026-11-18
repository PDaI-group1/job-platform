from pydantic import BaseModel, Field


class Experience(BaseModel):
    title: str = Field(description="Job title or role")
    years: float | None = Field(None, description="Years in this role; null if not stated")


class CVProfile(BaseModel):
    skills: list[str] = Field(
        description="Skills as mentioned in the CV, in their original wording"
    )
    skills_esco: list[str] = Field(
        description="Skills normalised to ESCO standard names",
        default_factory=list,
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
