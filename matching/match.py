"""
Compute a match score between a CV profile and a job's requirements.

No LLM is involved — matching is done in code using exact string comparison
and sentence embeddings.

Usage:
    python -m matching.match <cv_file> <job_ad_file>

Both files are processed through the normal extraction pipeline first.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim

from matching.cv_schemas import CVProfile
from matching.match_schemas import LanguageResult, MatchResult, SkillResult
from matching.schemas import JobRequirements

_MODEL_NAME = "all-MiniLM-L6-v2"

# Cosine similarity thresholds — untuned placeholders until evaluation set (#22).
MATCH_THRESHOLD = 0.75
PARTIAL_THRESHOLD = 0.50


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(_MODEL_NAME)


def match_cv_to_job(profile: CVProfile, requirements: JobRequirements) -> MatchResult:
    """Compare a CV profile against job requirements and return a scored result.

    Args:
        profile: Structured CV profile from build_cv_profile().
        requirements: Structured job requirements from extract_requirements().

    Returns:
        MatchResult with per-skill statuses and an overall score 0–100.
    """
    must_have = _match_requirements(requirements.must_have_skills, profile)
    nice_to_have = _match_requirements(requirements.nice_to_have_skills, profile)
    languages = _match_languages(requirements.required_languages, profile)
    score = _compute_score(must_have, nice_to_have)
    return MatchResult(score=score, must_have=must_have, nice_to_have=nice_to_have, languages=languages)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _cv_skill_strings(profile: CVProfile) -> list[str]:
    """All CV skills as strings: label if available, else raw."""
    return [sm.label if sm.label is not None else sm.raw for sm in profile.skill_matches]


def _exact_lookup(profile: CVProfile) -> dict[str, str]:
    """Case-insensitive map from every CV skill string to its display form.

    Label takes priority over raw so that exact matches surface the normalised name.
    """
    lookup: dict[str, str] = {}
    for sm in profile.skill_matches:
        lookup[sm.raw.lower()] = sm.label if sm.label is not None else sm.raw
        if sm.label is not None:
            lookup[sm.label.lower()] = sm.label
    return lookup


def _match_requirements(
    requirements: list[list[str]],
    profile: CVProfile,
) -> list[SkillResult]:
    if not requirements:
        return []

    exact = _exact_lookup(profile)
    cv_strings = _cv_skill_strings(profile)

    results: list[SkillResult | None] = [None] * len(requirements)
    needs_embedding: list[int] = []

    # Pass 1: exact case-insensitive match.
    for i, alternatives in enumerate(requirements):
        matched_by: str | None = None
        for alt in alternatives:
            hit = exact.get(alt.lower())
            if hit is not None:
                matched_by = hit
                break
        if matched_by is not None:
            results[i] = SkillResult(skill=alternatives, status="matched", matched_by=matched_by, score=1.0)
        else:
            needs_embedding.append(i)

    # Pass 2: embedding match for everything not caught by exact match.
    if needs_embedding:
        if not cv_strings:
            # No CV skills to compare against — everything is missing.
            for i in needs_embedding:
                results[i] = SkillResult(skill=requirements[i], status="missing", matched_by=None, score=0.0)
        else:
            model = _get_model()
            cv_vecs = model.encode(cv_strings, convert_to_tensor=True, show_progress_bar=False)

            # Encode all alternatives from all pending requirements in one batch.
            pending_alts: list[str] = [alt for i in needs_embedding for alt in requirements[i]]
            alt_vecs = model.encode(pending_alts, convert_to_tensor=True, show_progress_bar=False)
            sim = cos_sim(alt_vecs, cv_vecs).numpy()  # shape: (total_alts, n_cv_skills)

            alt_offset = 0
            for i in needs_embedding:
                alternatives = requirements[i]
                n_alts = len(alternatives)
                block = sim[alt_offset : alt_offset + n_alts]  # (n_alts, n_cv_skills)
                best_alt_idx, best_cv_idx = np.unravel_index(int(np.argmax(block)), block.shape)
                score = round(float(block[best_alt_idx, best_cv_idx]), 3)

                if score >= MATCH_THRESHOLD:
                    status: str = "matched"
                    matched_by = cv_strings[best_cv_idx]
                elif score >= PARTIAL_THRESHOLD:
                    status = "partial"
                    matched_by = cv_strings[best_cv_idx]
                else:
                    status = "missing"
                    matched_by = None

                results[i] = SkillResult(skill=alternatives, status=status, matched_by=matched_by, score=score)
                alt_offset += n_alts

    return results  # type: ignore[return-value]  # all slots filled above


def _match_languages(
    requirements: list,  # list[LanguageRequirement]
    profile: CVProfile,
) -> list[LanguageResult]:
    cv_langs = {lang.code.lower(): lang.level for lang in profile.languages}
    return [
        LanguageResult(
            code=req.code,
            requirement=req.requirement,
            cv_level=cv_langs.get(req.code.lower()),
        )
        for req in requirements
    ]


def _skill_points(results: list[SkillResult]) -> float:
    """Fraction of requirements met: matched=1, partial=0.5, missing=0."""
    if not results:
        return 0.0
    total = sum(
        1.0 if r.status == "matched" else 0.5 if r.status == "partial" else 0.0
        for r in results
    )
    return total / len(results)


def _compute_score(must_have: list[SkillResult], nice_to_have: list[SkillResult]) -> float:
    """Return a 0–100 score based on skills only (languages excluded).

    - Both present: must-haves 80 %, nice-to-haves 20 %.
    - Must-haves only: score on must-haves alone.
    - Nice-to-haves only (unusual): score on nice-to-haves alone.
    - Neither: 0.
    """
    must_score = _skill_points(must_have)
    nice_score = _skill_points(nice_to_have)

    if must_have and nice_to_have:
        raw = must_score * 0.8 + nice_score * 0.2
    elif must_have:
        raw = must_score
    elif nice_to_have:
        raw = nice_score
    else:
        raw = 0.0

    return round(raw * 100)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import json

    from matching.cv_extract import build_cv_profile
    from matching.extract import extract_requirements

    parser = argparse.ArgumentParser(description="Match a CV against a job ad")
    parser.add_argument("cv", type=Path, help="Plain-text CV file")
    parser.add_argument("ad", type=Path, help="Plain-text job ad file")
    args = parser.parse_args()

    profile = build_cv_profile(args.cv.read_text(encoding="utf-8"))
    requirements = extract_requirements(args.ad.read_text(encoding="utf-8"))
    result = match_cv_to_job(profile, requirements)
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
