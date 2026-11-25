"""Tests for match.py — no API key or real embedding model needed."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from matching.cv_schemas import CVProfile, Language, SkillMatch
from matching.match import MATCH_THRESHOLD, PARTIAL_THRESHOLD, match_cv_to_job
from matching.match_schemas import MatchResult
from matching.schemas import JobRequirements, LanguageRequirement


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _profile(skills: list[tuple[str, str | None]]) -> CVProfile:
    """Build a CVProfile from (raw, label) pairs. Score is irrelevant for matching."""
    return CVProfile(
        skills=[raw for raw, _ in skills],
        skill_matches=[SkillMatch(raw=raw, label=label, score=1.0 if label else 0.3) for raw, label in skills],
        experience=[],
        education=[],
        languages=[],
    )


def _profile_with_langs(
    skills: list[tuple[str, str | None]],
    languages: list[tuple[str, str]],  # (code, level)
) -> CVProfile:
    p = _profile(skills)
    p.languages = [Language(code=code, level=level) for code, level in languages]  # type: ignore[assignment]
    return p


def _reqs(
    must: list[list[str]],
    nice: list[list[str]] | None = None,
    langs: list[tuple[str, str]] | None = None,
) -> JobRequirements:
    return JobRequirements(
        must_have_skills=must,
        nice_to_have_skills=nice or [],
        seniority=None,
        required_languages=[LanguageRequirement(code=c, requirement=r) for c, r in (langs or [])],
    )


def _mock_model(scores: list[float]):
    """Return a model mock whose encode() returns vectors that produce the given cosine similarities.

    scores[i] is the similarity between the i-th alternative vector and the first CV skill vector.
    We use unit vectors along independent axes so cosine similarity equals the dot product.
    """
    n = len(scores)
    dim = n + 1  # +1 for the CV skill vector

    cv_vec = np.zeros((1, dim), dtype=np.float32)
    cv_vec[0, 0] = 1.0  # CV skill lives on axis 0

    alt_vecs = np.zeros((n, dim), dtype=np.float32)
    for i, s in enumerate(scores):
        alt_vecs[i, 0] = s          # component along CV axis → cos_sim = s
        remainder = max(0.0, 1.0 - s * s) ** 0.5
        alt_vecs[i, i + 1] = remainder  # orthogonal component to keep unit length

    call_count = 0

    def encode_side_effect(texts, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count % 2 == 1:
            # First call per requirement batch = CV skills
            return cv_vec
        else:
            return alt_vecs

    mock = MagicMock()
    mock.encode.side_effect = encode_side_effect
    return mock


# ---------------------------------------------------------------------------
# Exact matching
# ---------------------------------------------------------------------------

class TestExactMatch:
    def test_matches_by_label(self):
        profile = _profile([("py", "Python")])
        result = match_cv_to_job(profile, _reqs([["Python"]]))
        assert result.must_have[0].status == "matched"
        assert result.must_have[0].score == 1.0
        assert result.must_have[0].matched_by == "Python"

    def test_matches_by_raw_when_no_label(self):
        profile = _profile([("Python", None)])
        result = match_cv_to_job(profile, _reqs([["Python"]]))
        assert result.must_have[0].status == "matched"
        assert result.must_have[0].score == 1.0

    def test_case_insensitive(self):
        profile = _profile([("python", "Python")])
        result = match_cv_to_job(profile, _reqs([["PYTHON"]]))
        assert result.must_have[0].status == "matched"

    def test_exact_match_on_second_alternative(self):
        profile = _profile([("Go", "Go")])
        result = match_cv_to_job(profile, _reqs([["Rust", "Go", "C++"]]))
        assert result.must_have[0].status == "matched"
        assert result.must_have[0].matched_by == "Go"

    def test_no_exact_match_goes_to_embedding(self):
        # If there's no exact match, _get_model is called.
        profile = _profile([("TypeScript", "TypeScript")])
        with patch("matching.match._get_model") as mock_get:
            mock_get.return_value = _mock_model([0.9])
            result = match_cv_to_job(profile, _reqs([["JavaScript"]]))
        assert result.must_have[0].status == "matched"


# ---------------------------------------------------------------------------
# Embedding matching
# ---------------------------------------------------------------------------

class TestEmbeddingMatch:
    def _run(self, similarity: float) -> MatchResult:
        profile = _profile([("TypeScript", "TypeScript")])
        with patch("matching.match._get_model") as mock_get:
            mock_get.return_value = _mock_model([similarity])
            return match_cv_to_job(profile, _reqs([["JavaScript"]]))

    def test_above_match_threshold(self):
        result = self._run(MATCH_THRESHOLD)
        assert result.must_have[0].status == "matched"

    def test_between_thresholds_is_partial(self):
        mid = (MATCH_THRESHOLD + PARTIAL_THRESHOLD) / 2
        result = self._run(mid)
        assert result.must_have[0].status == "partial"

    def test_below_partial_threshold_is_missing(self):
        result = self._run(PARTIAL_THRESHOLD - 0.01)
        assert result.must_have[0].status == "missing"
        assert result.must_have[0].matched_by is None

    def test_missing_still_records_best_score(self):
        score = PARTIAL_THRESHOLD - 0.1
        result = self._run(score)
        assert result.must_have[0].score == pytest.approx(score, abs=0.01)

    def test_best_alternative_wins(self):
        """The requirement has two alternatives; the second scores higher."""
        profile = _profile([("TypeScript", "TypeScript")])
        with patch("matching.match._get_model") as mock_get:
            mock_get.return_value = _mock_model([0.4, 0.9])
            result = match_cv_to_job(profile, _reqs([["Rust", "JavaScript"]]))
        assert result.must_have[0].status == "matched"


# ---------------------------------------------------------------------------
# No CV skills
# ---------------------------------------------------------------------------

class TestNoCvSkills:
    def test_all_missing_when_no_cv_skills(self):
        profile = _profile([])
        result = match_cv_to_job(profile, _reqs([["Python"], ["Docker"]]))
        assert all(r.status == "missing" for r in result.must_have)
        assert all(r.score == 0.0 for r in result.must_have)
        assert result.score == 0


# ---------------------------------------------------------------------------
# Scoring edge cases
# ---------------------------------------------------------------------------

class TestScoring:
    def test_all_matched_scores_100(self):
        profile = _profile([("Python", "Python"), ("Docker", "Docker")])
        result = match_cv_to_job(profile, _reqs([["Python"], ["Docker"]]))
        assert result.score == 100

    def test_all_missing_scores_0(self):
        profile = _profile([])
        result = match_cv_to_job(profile, _reqs([["Python"]]))
        assert result.score == 0

    def test_no_nice_to_haves_scores_on_must_haves_only(self):
        profile = _profile([("Python", "Python")])
        result = match_cv_to_job(profile, _reqs([["Python"]], nice=None))
        assert result.score == 100
        assert result.nice_to_have == []

    def test_no_must_haves_scores_on_nice_to_haves(self):
        profile = _profile([("Python", "Python")])
        result = match_cv_to_job(profile, _reqs([], nice=[["Python"]]))
        assert result.score == 100
        assert result.must_have == []

    def test_no_requirements_scores_0(self):
        profile = _profile([("Python", "Python")])
        result = match_cv_to_job(profile, _reqs([]))
        assert result.score == 0

    def test_nice_to_haves_weighted_20_percent(self):
        # 1 must-have matched (score 1.0), 1 nice-to-have missing (score 0.0)
        # expected: 1.0 * 0.8 + 0.0 * 0.2 = 0.8 → 80
        profile = _profile([("Python", "Python")])
        result = match_cv_to_job(profile, _reqs([["Python"]], nice=[["Java"]]))
        assert result.score == 80

    def test_partial_must_have_scores_50(self):
        profile = _profile([("TypeScript", "TypeScript")])
        mid = (MATCH_THRESHOLD + PARTIAL_THRESHOLD) / 2
        with patch("matching.match._get_model") as mock_get:
            mock_get.return_value = _mock_model([mid])
            result = match_cv_to_job(profile, _reqs([["JavaScript"]]))
        assert result.score == 50


# ---------------------------------------------------------------------------
# Languages
# ---------------------------------------------------------------------------

class TestLanguages:
    def test_language_found_in_cv(self):
        profile = _profile_with_langs([], [("fi", "native"), ("en", "fluent")])
        result = match_cv_to_job(profile, _reqs([], langs=[("fi", "required")]))
        assert result.languages[0].code == "fi"
        assert result.languages[0].cv_level == "native"

    def test_language_not_in_cv(self):
        profile = _profile_with_langs([], [("en", "fluent")])
        result = match_cv_to_job(profile, _reqs([], langs=[("fi", "required")]))
        assert result.languages[0].cv_level is None

    def test_language_code_case_insensitive(self):
        profile = _profile_with_langs([], [("FI", "native")])
        result = match_cv_to_job(profile, _reqs([], langs=[("fi", "required")]))
        assert result.languages[0].cv_level == "native"

    def test_languages_not_in_score(self):
        # Even if all languages are missing, score is based on skills only.
        profile = _profile([("Python", "Python")])
        result = match_cv_to_job(profile, _reqs([["Python"]], langs=[("fi", "required")]))
        assert result.score == 100
