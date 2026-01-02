"""
Tests for Sganarelle Constants

Tests helper functions and constant values.
"""

import pytest
from src.sganarelle.constants import (
    clamp,
    rating_to_score,
    score_to_rating,
    # Constants validation
    EXPLICIT_FEEDBACK_WEIGHT,
    IMPLICIT_FEEDBACK_WEIGHT,
    RATING_MIN,
    RATING_MAX,
    SCORE_MIN,
    SCORE_MAX
)


class TestClamp:
    """Test clamp function"""

    def test_clamp_within_bounds(self):
        """Value within bounds stays unchanged"""
        assert clamp(0.5) == 0.5
        assert clamp(0.0) == 0.0
        assert clamp(1.0) == 1.0

    def test_clamp_below_min(self):
        """Value below min is clamped to min"""
        assert clamp(-0.5) == 0.0
        assert clamp(-10.0) == 0.0

    def test_clamp_above_max(self):
        """Value above max is clamped to max"""
        assert clamp(1.5) == 1.0
        assert clamp(10.0) == 1.0

    def test_clamp_custom_bounds(self):
        """Custom bounds work correctly"""
        assert clamp(5, min_val=0, max_val=10) == 5
        assert clamp(-5, min_val=0, max_val=10) == 0
        assert clamp(15, min_val=0, max_val=10) == 10

    def test_clamp_with_negative_range(self):
        """Negative ranges work"""
        assert clamp(0, min_val=-1.0, max_val=1.0) == 0.0
        assert clamp(-0.5, min_val=-1.0, max_val=1.0) == -0.5
        assert clamp(-2.0, min_val=-1.0, max_val=1.0) == -1.0


class TestRatingConversion:
    """Test rating <-> score conversion functions"""

    def test_rating_to_score_min(self):
        """Rating 1 → score 0.0"""
        assert rating_to_score(1) == 0.0

    def test_rating_to_score_max(self):
        """Rating 5 → score 1.0"""
        assert rating_to_score(5) == 1.0

    def test_rating_to_score_middle(self):
        """Rating 3 → score 0.5"""
        assert rating_to_score(3) == 0.5

    def test_rating_to_score_all_values(self):
        """All ratings convert correctly"""
        expected = {
            1: 0.0,
            2: 0.25,
            3: 0.5,
            4: 0.75,
            5: 1.0
        }
        for rating, score in expected.items():
            assert rating_to_score(rating) == pytest.approx(score)

    def test_rating_to_score_invalid_low(self):
        """Rating < 1 raises ValueError"""
        with pytest.raises(ValueError, match="Rating must be 1-5"):
            rating_to_score(0)

    def test_rating_to_score_invalid_high(self):
        """Rating > 5 raises ValueError"""
        with pytest.raises(ValueError, match="Rating must be 1-5"):
            rating_to_score(6)

    def test_score_to_rating_min(self):
        """Score 0.0 → rating 1"""
        assert score_to_rating(0.0) == 1

    def test_score_to_rating_max(self):
        """Score 1.0 → rating 5"""
        assert score_to_rating(1.0) == 5

    def test_score_to_rating_middle(self):
        """Score 0.5 → rating 3"""
        assert score_to_rating(0.5) == 3

    def test_score_to_rating_rounding(self):
        """Scores round correctly to ratings"""
        assert score_to_rating(0.1) == 1
        assert score_to_rating(0.3) == 2
        assert score_to_rating(0.6) == 3
        assert score_to_rating(0.8) == 4

    def test_score_to_rating_invalid_low(self):
        """Score < 0 raises ValueError"""
        with pytest.raises(ValueError, match="Score must be 0.0-1.0"):
            score_to_rating(-0.1)

    def test_score_to_rating_invalid_high(self):
        """Score > 1 raises ValueError"""
        with pytest.raises(ValueError, match="Score must be 0.0-1.0"):
            score_to_rating(1.1)

    def test_rating_score_roundtrip(self):
        """Rating → Score → Rating roundtrip works"""
        for rating in range(RATING_MIN, RATING_MAX + 1):
            score = rating_to_score(rating)
            back = score_to_rating(score)
            assert back == rating


class TestConstantValues:
    """Test constant values are valid"""

    def test_feedback_weights_sum_to_one(self):
        """Feedback weights sum to 1.0"""
        assert EXPLICIT_FEEDBACK_WEIGHT + IMPLICIT_FEEDBACK_WEIGHT == pytest.approx(1.0)

    def test_feedback_weights_in_range(self):
        """Feedback weights are in [0, 1]"""
        assert 0 <= EXPLICIT_FEEDBACK_WEIGHT <= 1
        assert 0 <= IMPLICIT_FEEDBACK_WEIGHT <= 1

    def test_score_bounds_valid(self):
        """Score min < max"""
        assert SCORE_MIN < SCORE_MAX
        assert SCORE_MIN == 0.0
        assert SCORE_MAX == 1.0

    def test_rating_bounds_valid(self):
        """Rating min < max"""
        assert RATING_MIN < RATING_MAX
        assert RATING_MIN == 1
        assert RATING_MAX == 5
