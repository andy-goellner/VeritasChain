"""Scoring logic for PoCiv civility ratings."""

from typing import Literal


def calculate_score(metrics: list[int]) -> float:
    """
    Calculate the average score from 5 metrics.

    Args:
        metrics: List of 5 integers (0-5) representing:
            [0]: Clarity
            [1]: Respectfulness
            [2]: Relevance
            [3]: Evidence
            [4]: Constructiveness

    Returns:
        Average score as float (0-5)

    Raises:
        ValueError: If metrics list doesn't have exactly 5 elements
                   or if any metric is outside 0-5 range
    """
    if len(metrics) != 5:
        raise ValueError(f"Expected 5 metrics, got {len(metrics)}")

    for i, metric in enumerate(metrics):
        if not isinstance(metric, int) or metric < 0 or metric > 5:
            raise ValueError(f"Metric {i} must be an integer between 0 and 5, got {metric}")

    return sum(metrics) / 5.0


def get_tier(score: float) -> Literal["Bronze", "Silver", "Gold"] | None:
    """
    Determine the tier based on the calculated score.

    Args:
        score: The calculated score (0-5)

    Returns:
        Tier name ("Bronze", "Silver", "Gold") or None if score < 3.0
    """
    if score < 3.0:
        return None
    elif 3.0 <= score < 4.0:
        return "Bronze"
    elif 4.0 <= score < 4.6:
        return "Silver"
    else:  # 4.6 <= score <= 5.0
        return "Gold"


def get_emoji(tier: str) -> str:
    """
    Get the emoji for a given tier.

    Args:
        tier: Tier name ("Bronze", "Silver", "Gold")

    Returns:
        Emoji string (🥉, 🥈, or 🥇)

    Raises:
        ValueError: If tier is not one of the valid tiers
    """
    emoji_map = {
        "Bronze": "🥉",
        "Silver": "🥈",
        "Gold": "🥇",
    }
    if tier not in emoji_map:
        raise ValueError(f"Invalid tier: {tier}. Must be one of {list(emoji_map.keys())}")
    return emoji_map[tier]

