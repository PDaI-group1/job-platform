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

- must_have_skills: skills and qualifications the posting states are required
- nice_to_have_skills: skills mentioned as a plus, beneficial, or preferred
- seniority: one of junior / mid / senior / lead — null if not stated or unclear
- required_languages: human languages required or expected (e.g. Finnish, English)

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
