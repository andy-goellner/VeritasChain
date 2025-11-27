"""Tests for scoring logic."""

import pytest

from src.scoring import calculate_score, get_emoji, get_tier


def test_calculate_score_valid_inputs() -> None:
    """Test score calculation with valid inputs."""
    metrics = [5, 4, 3, 2, 1]
    score = calculate_score(metrics)
    assert score == 3.0


def test_calculate_score_all_fives() -> None:
    """Test score calculation with all 5s."""
    metrics = [5, 5, 5, 5, 5]
    score = calculate_score(metrics)
    assert score == 5.0


def test_calculate_score_all_zeros() -> None:
    """Test score calculation with all 0s."""
    metrics = [0, 0, 0, 0, 0]
    score = calculate_score(metrics)
    assert score == 0.0


def test_calculate_score_wrong_length() -> None:
    """Test that wrong number of metrics raises ValueError."""
    with pytest.raises(ValueError, match="Expected 5 metrics"):
        calculate_score([1, 2, 3])


def test_calculate_score_out_of_range() -> None:
    """Test that out-of-range metrics raise ValueError."""
    with pytest.raises(ValueError):
        calculate_score([1, 2, 3, 4, 6])  # 6 is out of range

    with pytest.raises(ValueError):
        calculate_score([1, 2, 3, 4, -1])  # -1 is out of range


def test_get_tier_bronze() -> None:
    """Test tier determination for Bronze."""
    assert get_tier(3.0) == "Bronze"
    assert get_tier(3.5) == "Bronze"
    assert get_tier(3.9) == "Bronze"


def test_get_tier_silver() -> None:
    """Test tier determination for Silver."""
    assert get_tier(4.0) == "Silver"
    assert get_tier(4.25) == "Silver"
    assert get_tier(4.5) == "Silver"


def test_get_tier_gold() -> None:
    """Test tier determination for Gold."""
    assert get_tier(4.6) == "Gold"
    assert get_tier(5.0) == "Gold"


def test_get_tier_below_threshold() -> None:
    """Test tier determination for scores below 3.0."""
    assert get_tier(2.9) is None
    assert get_tier(0.0) is None


def test_get_emoji_bronze() -> None:
    """Test emoji for Bronze tier."""
    assert get_emoji("Bronze") == "🥉"


def test_get_emoji_silver() -> None:
    """Test emoji for Silver tier."""
    assert get_emoji("Silver") == "🥈"


def test_get_emoji_gold() -> None:
    """Test emoji for Gold tier."""
    assert get_emoji("Gold") == "🥇"


def test_get_emoji_invalid_tier() -> None:
    """Test that invalid tier raises ValueError."""
    with pytest.raises(ValueError):
        get_emoji("Invalid")

