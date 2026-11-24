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
from matching.esco import normalise_skills
from matching.llm import generate_json
from matching.privacy import redact_contacts

_MAX_TEXT_LEN = 30_000

_SYSTEM = """\
You are a CV parser. Extract the following from the CV the user provides.
The CV may be written in Finnish, English, Swedish, or a mix.

- skills: all technical and professional skills mentioned, in their original wording
- experience: each work experience entry as a job title and years (null if not stated).
  Convert months to years: e.g. "3 months" → 0.25, "6 months" → 0.5.
- education: degrees, qualifications or fields of study
- languages: human languages the candidate speaks or mentions.
  Output each as an ISO 639-1 code (e.g. "fi", "en", "sv", "zh", "ar").
  Map stated proficiency to: native / fluent / good / basic. Set level to null if not stated.
  Examples: "äidinkieli" or "native" → native; "fluent" or "sujuva" → fluent;
  "good" or "hyvä" → good; "basic" or "perustaso" → basic.

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


def build_cv_profile(text: str) -> CVProfile:
    """Full pipeline: validate → redact → extract → normalise skills.

    This is the entry point for the background worker.

    Args:
        text: Plain text of the CV.

    Returns:
        CVProfile ready for storage. Serialises cleanly with
        ``profile.model_dump(mode="json")``.

    Raises:
        ValueError: If text is empty/whitespace or longer than 30 000 characters.
        google.genai.errors.APIError: On API errors.
        ValueError: If GEMINI_API_KEY is not set.
    """
    if not text or not text.strip():
        raise ValueError("CV text must not be empty")
    if len(text) > _MAX_TEXT_LEN:
        raise ValueError(f"CV text exceeds {_MAX_TEXT_LEN} characters ({len(text)})")

    clean = redact_contacts(text)
    profile = extract_cv_profile(clean)
    profile.skill_matches = normalise_skills(profile.skills)
    return profile


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract a skills profile from a CV text file")
    parser.add_argument("file", type=Path, help="Path to a plain-text CV")
    args = parser.parse_args()

    cv_text = args.file.read_text(encoding="utf-8")
    result = build_cv_profile(cv_text)
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
