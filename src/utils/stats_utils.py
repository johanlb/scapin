"""
Statistical Utilities

Centralized statistics calculation functions to eliminate code duplication
across the codebase.

Usage:
    from src.utils.stats_utils import calculate_percentiles, calculate_average

    data = [1.0, 2.5, 3.7, 4.2, 5.1]
    p50, p95, p99 = calculate_percentiles(data, [50, 95, 99])
    avg = calculate_average(data)
"""

from typing import Optional, Union


def calculate_average(values: list[Union[int, float]]) -> float:
    """
    Calculate average of numeric values

    Args:
        values: List of numbers

    Returns:
        Average value, or 0.0 if empty list

    Examples:
        >>> calculate_average([1, 2, 3, 4, 5])
        3.0
        >>> calculate_average([])
        0.0
        >>> calculate_average([42])
        42.0
    """
    if not values:
        return 0.0

    return sum(values) / len(values)


def calculate_percentile(
    values: list[Union[int, float]],
    percentile: int
) -> float:
    """
    Calculate a specific percentile of numeric values

    Uses the nearest-rank method with proper bounds checking.

    Args:
        values: List of numbers (will be sorted internally)
        percentile: Percentile to calculate (0-100)

    Returns:
        Percentile value, or 0.0 if empty list

    Raises:
        ValueError: If percentile not in range 0-100

    Examples:
        >>> calculate_percentile([1, 2, 3, 4, 5], 50)
        3.0
        >>> calculate_percentile([1, 2, 3, 4, 5], 95)
        5.0
        >>> calculate_percentile([42], 50)
        42.0
        >>> calculate_percentile([], 50)
        0.0
    """
    if not isinstance(percentile, int) or not (0 <= percentile <= 100):
        raise ValueError(f"Percentile must be integer 0-100, got: {percentile}")

    if not values:
        return 0.0

    if len(values) == 1:
        return float(values[0])

    # Sort values
    sorted_values = sorted(values)
    n = len(sorted_values)

    # Calculate index with proper bounds checking
    # For percentile p, index = int((n-1) * p/100)
    # This ensures p=0 -> idx=0, p=100 -> idx=n-1
    idx = min(int((n - 1) * percentile / 100), n - 1)

    return float(sorted_values[idx])


def calculate_percentiles(
    values: list[Union[int, float]],
    percentiles: list[int]
) -> dict[int, float]:
    """
    Calculate multiple percentiles at once

    More efficient than calling calculate_percentile multiple times
    because it only sorts the values once.

    Args:
        values: List of numbers
        percentiles: List of percentiles to calculate (e.g., [50, 95, 99])

    Returns:
        Dictionary mapping percentile -> value

    Raises:
        ValueError: If any percentile not in range 0-100

    Examples:
        >>> calculate_percentiles([1, 2, 3, 4, 5], [50, 95, 99])
        {50: 3.0, 95: 5.0, 99: 5.0}
        >>> calculate_percentiles([42], [50, 95, 99])
        {50: 42.0, 95: 42.0, 99: 42.0}
        >>> calculate_percentiles([], [50, 95])
        {50: 0.0, 95: 0.0}
    """
    # Validate percentiles
    for p in percentiles:
        if not isinstance(p, int) or not (0 <= p <= 100):
            raise ValueError(f"Percentile must be integer 0-100, got: {p}")

    # Handle empty list
    if not values:
        return dict.fromkeys(percentiles, 0.0)

    # Handle single value
    if len(values) == 1:
        return {p: float(values[0]) for p in percentiles}

    # Sort once for efficiency
    sorted_values = sorted(values)
    n = len(sorted_values)

    # Calculate all percentiles
    result = {}
    for p in percentiles:
        idx = min(int((n - 1) * p / 100), n - 1)
        result[p] = float(sorted_values[idx])

    return result


def calculate_stats_summary(
    values: list[Union[int, float]],
    percentiles: Optional[list[int]] = None
) -> dict[str, float]:
    """
    Calculate comprehensive stats summary

    Calculates average and percentiles in one call.

    Args:
        values: List of numbers
        percentiles: List of percentiles to calculate (default: [50, 95, 99])

    Returns:
        Dictionary with 'average', 'p50', 'p95', 'p99', etc.

    Examples:
        >>> calculate_stats_summary([1, 2, 3, 4, 5])
        {'average': 3.0, 'p50': 3.0, 'p95': 5.0, 'p99': 5.0}
        >>> calculate_stats_summary([1, 2, 3], percentiles=[25, 50, 75])
        {'average': 2.0, 'p25': 1.0, 'p50': 2.0, 'p75': 3.0}
    """
    if percentiles is None:
        percentiles = [50, 95, 99]

    result = {"average": calculate_average(values)}

    # Add percentiles
    percentile_values = calculate_percentiles(values, percentiles)
    for p, value in percentile_values.items():
        result[f"p{p}"] = value

    return result


def calculate_rate(
    count: int,
    duration_seconds: float
) -> float:
    """
    Calculate rate (items per second)

    Args:
        count: Number of items
        duration_seconds: Time duration in seconds

    Returns:
        Rate as items/second, or 0.0 if duration is 0

    Examples:
        >>> calculate_rate(100, 10.0)
        10.0
        >>> calculate_rate(50, 5.0)
        10.0
        >>> calculate_rate(100, 0.0)
        0.0
    """
    if duration_seconds <= 0:
        return 0.0

    return count / duration_seconds


def calculate_rate_per_minute(
    count: int,
    duration_minutes: float
) -> float:
    """
    Calculate rate (items per minute)

    Args:
        count: Number of items
        duration_minutes: Time duration in minutes

    Returns:
        Rate as items/minute, or 0.0 if duration is 0

    Examples:
        >>> calculate_rate_per_minute(60, 1.0)
        60.0
        >>> calculate_rate_per_minute(120, 2.0)
        60.0
        >>> calculate_rate_per_minute(100, 0.0)
        0.0
    """
    if duration_minutes <= 0:
        return 0.0

    return count / duration_minutes
