from unittest.mock import MagicMock, patch

import pytest

from matching.cv_extract import _MAX_TEXT_LEN, build_cv_profile
from matching.cv_schemas import CVExtraction


def _mock_extraction():
    return CVExtraction(skills=[], experience=[], education=[], languages=[])


class TestBuildCvProfileValidation:
    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="empty"):
            build_cv_profile("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="empty"):
            build_cv_profile("   \n\t  ")

    def test_too_long_raises(self):
        text = "x" * (_MAX_TEXT_LEN + 1)
        with pytest.raises(ValueError, match=str(_MAX_TEXT_LEN)):
            build_cv_profile(text)

    def test_exactly_at_limit_passes_validation(self):
        # Text at the limit should pass the length check — patch the API so we don't hit Gemini.
        text = "x" * _MAX_TEXT_LEN
        with patch("matching.cv_extract.generate_json", return_value=_mock_extraction()):
            with patch("matching.cv_extract.normalise_skills", return_value=[]):
                profile = build_cv_profile(text)
        assert profile is not None
