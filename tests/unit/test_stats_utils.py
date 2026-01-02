"""
Tests for Statistical Utilities (H2-1)

Covers:
- Average calculation
- Percentile calculation (single and multiple)
- Stats summary
- Rate calculation
- Edge cases (empty lists, single values)
"""

import pytest
from src.utils.stats_utils import (
    calculate_average,
    calculate_percentile,
    calculate_percentiles,
    calculate_stats_summary,
    calculate_rate,
    calculate_rate_per_minute,
)


class TestCalculateAverage:
    """Test average calculation"""

    def test_average_of_integers(self):
        """Test average with integers"""
        assert calculate_average([1, 2, 3, 4, 5]) == 3.0

    def test_average_of_floats(self):
        """Test average with floats"""
        assert calculate_average([1.5, 2.5, 3.5]) == pytest.approx(2.5)

    def test_average_of_mixed(self):
        """Test average with mixed int/float"""
        assert calculate_average([1, 2.5, 3, 4.5]) == pytest.approx(2.75)

    def test_average_empty_list(self):
        """Test average of empty list returns 0.0"""
        assert calculate_average([]) == 0.0

    def test_average_single_value(self):
        """Test average of single value"""
        assert calculate_average([42]) == 42.0
        assert calculate_average([3.14]) == pytest.approx(3.14)


class TestCalculatePercentile:
    """Test single percentile calculation"""

    def test_percentile_50_median(self):
        """Test 50th percentile (median)"""
        assert calculate_percentile([1, 2, 3, 4, 5], 50) == 3.0

    def test_percentile_95(self):
        """Test 95th percentile"""
        values = list(range(1, 101))  # 1 to 100
        result = calculate_percentile(values, 95)
        assert result == 95.0

    def test_percentile_99(self):
        """Test 99th percentile"""
        values = list(range(1, 101))  # 1 to 100
        result = calculate_percentile(values, 99)
        assert result == 99.0

    def test_percentile_0_min(self):
        """Test 0th percentile (minimum)"""
        assert calculate_percentile([5, 3, 8, 1, 9], 0) == 1.0

    def test_percentile_100_max(self):
        """Test 100th percentile (maximum)"""
        assert calculate_percentile([5, 3, 8, 1, 9], 100) == 9.0

    def test_percentile_empty_list(self):
        """Test percentile of empty list returns 0.0"""
        assert calculate_percentile([], 50) == 0.0

    def test_percentile_single_value(self):
        """Test percentile of single value returns that value"""
        assert calculate_percentile([42], 50) == 42.0
        assert calculate_percentile([42], 95) == 42.0

    def test_percentile_invalid_range(self):
        """Test percentile raises error for invalid range"""
        with pytest.raises(ValueError, match="Percentile must be integer 0-100"):
            calculate_percentile([1, 2, 3], -1)

        with pytest.raises(ValueError, match="Percentile must be integer 0-100"):
            calculate_percentile([1, 2, 3], 101)

    def test_percentile_non_integer(self):
        """Test percentile raises error for non-integer"""
        with pytest.raises(ValueError, match="Percentile must be integer 0-100"):
            calculate_percentile([1, 2, 3], 50.5)


class TestCalculatePercentiles:
    """Test multiple percentiles calculation"""

    def test_percentiles_standard(self):
        """Test standard percentiles (50, 95, 99)"""
        values = list(range(1, 101))
        result = calculate_percentiles(values, [50, 95, 99])

        assert result[50] == 50.0
        assert result[95] == 95.0
        assert result[99] == 99.0

    def test_percentiles_custom(self):
        """Test custom percentiles"""
        values = [1, 2, 3, 4, 5]
        result = calculate_percentiles(values, [25, 50, 75])

        assert result[25] == 2.0
        assert result[50] == 3.0
        assert result[75] == 4.0

    def test_percentiles_empty_list(self):
        """Test percentiles of empty list"""
        result = calculate_percentiles([], [50, 95, 99])

        assert result[50] == 0.0
        assert result[95] == 0.0
        assert result[99] == 0.0

    def test_percentiles_single_value(self):
        """Test percentiles of single value"""
        result = calculate_percentiles([42], [50, 95, 99])

        assert result[50] == 42.0
        assert result[95] == 42.0
        assert result[99] == 42.0

    def test_percentiles_invalid_range(self):
        """Test percentiles raises error for invalid range"""
        with pytest.raises(ValueError, match="Percentile must be integer 0-100"):
            calculate_percentiles([1, 2, 3], [50, 101])

        with pytest.raises(ValueError, match="Percentile must be integer 0-100"):
            calculate_percentiles([1, 2, 3], [-1, 50])


class TestCalculateStatsSummary:
    """Test comprehensive stats summary"""

    def test_stats_summary_default_percentiles(self):
        """Test stats summary with default percentiles [50, 95, 99]"""
        values = list(range(1, 101))
        result = calculate_stats_summary(values)

        assert result["average"] == 50.5
        assert result["p50"] == 50.0
        assert result["p95"] == 95.0
        assert result["p99"] == 99.0

    def test_stats_summary_custom_percentiles(self):
        """Test stats summary with custom percentiles"""
        values = [1, 2, 3, 4, 5]
        result = calculate_stats_summary(values, percentiles=[25, 50, 75])

        assert result["average"] == 3.0
        assert result["p25"] == 2.0
        assert result["p50"] == 3.0
        assert result["p75"] == 4.0

    def test_stats_summary_empty_list(self):
        """Test stats summary of empty list"""
        result = calculate_stats_summary([])

        assert result["average"] == 0.0
        assert result["p50"] == 0.0
        assert result["p95"] == 0.0
        assert result["p99"] == 0.0


class TestCalculateRate:
    """Test rate calculation"""

    def test_rate_standard(self):
        """Test standard rate calculation"""
        assert calculate_rate(100, 10.0) == 10.0
        assert calculate_rate(50, 5.0) == 10.0

    def test_rate_fractional(self):
        """Test rate with fractional values"""
        assert calculate_rate(15, 3.5) == pytest.approx(4.2857, rel=0.001)

    def test_rate_zero_duration(self):
        """Test rate with zero duration returns 0.0"""
        assert calculate_rate(100, 0.0) == 0.0

    def test_rate_negative_duration(self):
        """Test rate with negative duration returns 0.0"""
        assert calculate_rate(100, -1.0) == 0.0

    def test_rate_zero_count(self):
        """Test rate with zero count"""
        assert calculate_rate(0, 10.0) == 0.0


class TestCalculateRatePerMinute:
    """Test rate per minute calculation"""

    def test_rate_per_minute_standard(self):
        """Test standard rate per minute"""
        assert calculate_rate_per_minute(60, 1.0) == 60.0
        assert calculate_rate_per_minute(120, 2.0) == 60.0

    def test_rate_per_minute_fractional(self):
        """Test rate per minute with fractional values"""
        assert calculate_rate_per_minute(45, 1.5) == 30.0

    def test_rate_per_minute_zero_duration(self):
        """Test rate per minute with zero duration returns 0.0"""
        assert calculate_rate_per_minute(100, 0.0) == 0.0

    def test_rate_per_minute_negative_duration(self):
        """Test rate per minute with negative duration returns 0.0"""
        assert calculate_rate_per_minute(100, -1.0) == 0.0


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_large_dataset(self):
        """Test with large dataset"""
        values = list(range(1, 100001))  # 100k values
        result = calculate_stats_summary(values)

        assert result["average"] == 50000.5
        assert result["p50"] == 50000.0
        assert result["p95"] == 95000.0
        assert result["p99"] == 99000.0

    def test_duplicate_values(self):
        """Test with duplicate values"""
        values = [1, 1, 1, 2, 2, 2, 3, 3, 3]
        result = calculate_stats_summary(values)

        assert result["average"] == 2.0
        assert result["p50"] == 2.0

    def test_unsorted_input(self):
        """Test that unsorted input works correctly"""
        values = [5, 2, 8, 1, 9, 3, 7, 4, 6]
        result = calculate_percentile(values, 50)

        # Should sort internally and find median
        assert result == 5.0
