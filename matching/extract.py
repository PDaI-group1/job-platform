"""
Extract structured requirements from a job ad using Gemini Flash.

Usage:
    python -m matching.extract <path-to-job-ad.txt>
    python -m matching.extract <path-to-job-ad.txt> --model gemini-1.5-flash

Requires GEMINI_API_KEY in .env or environment.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from matching.schemas import JobRequirements

load_dotenv()

DEFAULT_MODEL = "gemini-3.5-flash-lite"

_SYSTEM = """\
You are a job ad parser. Extract the following from the job ad the user provides.
The ad may be written in Finnish, English, Swedish, or a mix.

- must_have_skills: skills and qualifications the posting states are required
- nice_to_have_skills: skills mentioned as a plus, beneficial, or preferred
- seniority: one of junior / mid / senior / lead — null if not stated or unclear
- required_languages: human languages required or expected (e.g. Finnish, English)

Be precise. Only include information that is in the ad. Do not infer or add skills that are not mentioned.\
"""


def extract_requirements(text: str, model: str = DEFAULT_MODEL) -> JobRequirements:
    """Extract structured requirements from a plain-text job ad.

    Args:
        text: Plain text of the job ad (HTML already stripped).
        model: Gemini model ID to use.

    Returns:
        Validated JobRequirements.

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
            response_schema=JobRequirements,
        ),
    )

    return JobRequirements.model_validate_json(response.text)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract requirements from a job ad text file")
    parser.add_argument("file", type=Path, help="Path to a plain-text job ad")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Gemini model ID")
    args = parser.parse_args()

    ad_text = args.file.read_text(encoding="utf-8")
    result = extract_requirements(ad_text, model=args.model)
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
