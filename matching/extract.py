"""
Extract structured requirements from a job ad using Gemini.

Usage:
    python -m matching.extract <path-to-job-ad.txt>

Requires GEMINI_API_KEY in .env or environment.
Model is read from GEMINI_MODEL env var (default: gemini-3.5-flash-lite).
"""

import json
from pathlib import Path

from matching.llm import generate_json
from matching.schemas import JobRequirements

_SYSTEM = """\
You are a job ad parser. Extract the following from the job ad the user provides.
The ad may be written in Finnish, English, Swedish, or a mix.

- must_have_skills: required skills and qualifications. Each entry is a list of short alternative skill
  names for one requirement. Keep names short (1–3 words). Use English names for well-known tools and
  technologies even if the ad is in Finnish.
  Examples:
    "Java, TypeScript, C# or Python" → [["Java","TypeScript","C#","Python"]]
    "Strong IaC mastery (Terraform or Bicep)" → [["Terraform","Bicep"]]
    "5 years of Python experience" → [["Python"]]
  Single-skill requirements are still wrapped in a list: [["Python"]].

- nice_to_have_skills: skills mentioned as a plus, beneficial, or preferred. Same format as must_have_skills.

- seniority: one of junior / mid / senior / lead / intern — null if not stated or unclear.
  Use "intern" for trainee, harjoittelija, or similar roles.

- required_languages: human languages required or expected. For each, provide the ISO 639-1 code
  (e.g. "fi" for Finnish, "en" for English, "sv" for Swedish) and whether it is "required" or an "advantage".

Be precise. Only include information that is in the ad. Do not infer or add skills that are not mentioned.\
"""


def extract_requirements(text: str) -> JobRequirements:
    """Extract structured requirements from a plain-text job ad.

    Args:
        text: Plain text of the job ad (HTML already stripped).

    Returns:
        Validated JobRequirements.

    Raises:
        google.genai.errors.APIError: On API errors.
        ValueError: If GEMINI_API_KEY is not set.
    """
    return generate_json(_SYSTEM, text, JobRequirements)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract requirements from a job ad text file")
    parser.add_argument("file", type=Path, help="Path to a plain-text job ad")
    args = parser.parse_args()

    ad_text = args.file.read_text(encoding="utf-8")
    result = extract_requirements(ad_text)
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
