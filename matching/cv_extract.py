"""
Extract a structured skills profile from a CV using Gemini.

Usage:
    python -m matching.cv_extract <path-to-cv.txt>

Requires GEMINI_API_KEY in .env or environment.
Model is read from GEMINI_MODEL env var (default: gemini-3.5-flash-lite).
"""

import json
from pathlib import Path

from matching.cv_schemas import CVExtraction, CVProfile
from matching.llm import generate_json

_SYSTEM = """\
You are a CV parser. Extract the following from the CV the user provides.
The CV may be written in Finnish, English, Swedish, or a mix.

- skills: all technical and professional skills mentioned, in their original wording
- experience: each work experience entry as a job title and number of years (null if not stated)
- education: degrees, qualifications or fields of study
- languages: human languages the candidate speaks or mentions

Do not infer or add anything not stated in the CV.\
"""


def extract_cv_profile(text: str) -> CVProfile:
    """Extract a structured profile from plain-text CV content.

    Args:
        text: Plain text of the CV.

    Returns:
        CVProfile with skills, experience, education and languages.
        skill_matches is always empty — call normalise_skills() to populate it.

    Raises:
        google.genai.errors.APIError: On API errors.
        ValueError: If GEMINI_API_KEY is not set.
    """
    extraction = generate_json(_SYSTEM, text, CVExtraction)
    return CVProfile(**extraction.model_dump())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract a skills profile from a CV text file")
    parser.add_argument("file", type=Path, help="Path to a plain-text CV")
    args = parser.parse_args()

    cv_text = args.file.read_text(encoding="utf-8")
    result = extract_cv_profile(cv_text)
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
