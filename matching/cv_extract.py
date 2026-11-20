"""
Extract a structured skills profile from a CV using Gemini Flash.

Usage:
    python -m matching.cv_extract <path-to-cv.txt>
    python -m matching.cv_extract <path-to-cv.txt> --model gemini-3.8-flash

Requires GEMINI_API_KEY in .env or environment.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from matching.cv_schemas import CVExtraction, CVProfile

load_dotenv()

DEFAULT_MODEL = "gemini-3.5-flash-lite"

_SYSTEM = """\
You are a CV parser. Extract the following from the CV the user provides.
The CV may be written in Finnish, English, Swedish, or a mix.

- skills: all technical and professional skills mentioned, in their original wording
- experience: each work experience entry as a job title and number of years (null if not stated)
- education: degrees, qualifications or fields of study
- languages: human languages the candidate speaks or mentions

Do not infer or add anything not stated in the CV.\
"""


def extract_cv_profile(text: str, model: str = DEFAULT_MODEL) -> CVProfile:
    """Extract a structured profile from plain-text CV content.

    Args:
        text: Plain text of the CV.
        model: Gemini model ID to use.

    Returns:
        CVProfile with skills, experience, education and languages.
        skills_esco is always empty — call normalise_skills() to populate it.

    Raises:
        google.genai.errors.APIError: On API errors.
        ValueError: If GEMINI_API_KEY is not set.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set")

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=60_000),
    )
    response = client.models.generate_content(
        model=model,
        contents=text,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM,
            response_mime_type="application/json",
            response_schema=CVExtraction,
        ),
    )

    extraction = CVExtraction.model_validate_json(response.text)
    return CVProfile(**extraction.model_dump())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract a skills profile from a CV text file")
    parser.add_argument("file", type=Path, help="Path to a plain-text CV")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Gemini model ID")
    args = parser.parse_args()

    cv_text = args.file.read_text(encoding="utf-8")
    result = extract_cv_profile(cv_text, model=args.model)
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
