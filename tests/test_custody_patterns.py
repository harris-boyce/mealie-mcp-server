"""Unit tests for custody pattern library."""

import pytest
from datetime import date, timedelta
from src.utils.custody_patterns import (
    CustodyPattern,
    CUSTODY_PATTERNS,
    visualize_both_groups,
)


class TestPatternLibrary:
    """Test pattern library configuration."""

    def test_all_patterns_valid(self):
        """All patterns in library have valid configuration."""
        for pattern_name, config in CUSTODY_PATTERNS.items():
            assert "description" in config
            assert "cycle_days" in config
            assert "boys" in config
            assert "girls" in config

            cycle_days = config["cycle_days"]
            assert len(config["boys"]) == cycle_days, (
                f"{pattern_name}: boys array length mismatch"
            )
            assert len(config["girls"]) == cycle_days, (
                f"{pattern_name}: girls array length mismatch"
            )

    def test_pattern_names(self):
        """Verify expected patterns exist."""
        expected_patterns = {
            "2-5-5-2",
            "3-4-4-3",
            "2-2-3",
            "2-2-5-5",
            "week-on-week-off",
            "every-other-weekend",
            "2-2-3-2-2-3-blended",
        }
        assert set(CUSTODY_PATTERNS.keys()) == expected_patterns


class TestCustodyPatternInit:
    """Test CustodyPattern initialization."""

    def test_init_with_pattern_name(self):
        """Initialize with pattern name from library."""
        pattern = CustodyPattern(
            pattern_name="2-5-5-2",
            cycle_start="2026-01-05",
            group="boys"
        )
        assert pattern.pattern_name == "2-5-5-2"
        assert pattern.cycle_days == 14
        assert pattern.cycle_start == date(2026, 1, 5)
        assert pattern.group == "boys"

    def test_init_with_custom_pattern(self):
        """Initialize with custom pattern dict."""
        custom = {
            "description": "Test pattern",
            "cycle_days": 7,
            "boys": [True, False, True, False, True, False, True],
            "girls": [False, True, False, True, False, True, False],
        }
        pattern = CustodyPattern(
            custom_pattern=custom,
            cycle_start="2026-01-05",
            group="boys"
        )
        assert pattern.cycle_days == 7
        assert pattern.pattern_array == custom["boys"]

    def test_init_missing_pattern(self):
        """Raise error if no pattern provided."""
        with pytest.raises(ValueError, match="Must provide either pattern_name"):
            CustodyPattern(cycle_start="2026-01-05", group="boys")

    def test_init_invalid_pattern_name(self):
        """Raise error if pattern name not in library."""
        with pytest.raises(ValueError, match="Must provide either pattern_name"):
            CustodyPattern(
                pattern_name="invalid-pattern",
                cycle_start="2026-01-05",
                group="boys"
            )

    def test_init_missing_group_key(self):
        """Raise error if pattern missing group key."""
        custom = {
            "description": "Missing girls key",
            "cycle_days": 7,
            "boys": [True] * 7,
        }
        with pytest.raises(ValueError, match="Pattern missing 'girls' key"):
            CustodyPattern(
                custom_pattern=custom,
                cycle_start="2026-01-05",
                group="girls"
            )

    def test_init_invalid_array_length(self):
        """Raise error if pattern array length != cycle_days."""
        custom = {
            "description": "Wrong length",
            "cycle_days": 14,
            "boys": [True] * 7,  # Should be 14
            "girls": [True] * 7,
        }
        with pytest.raises(ValueError, match="Pattern array length"):
            CustodyPattern(
                custom_pattern=custom,
                cycle_start="2026-01-05",
                group="boys"
            )


class TestCustomBlendedPattern:
    """Test user's custom 2-2-3-2-2-3-blended pattern."""

    @pytest.fixture
    def boys_pattern(self):
        """Boys pattern instance."""
        return CustodyPattern(
            pattern_name="2-2-3-2-2-3-blended",
            cycle_start="2026-01-26",
            group="boys"
        )

    @pytest.fixture
    def girls_pattern(self):
        """Girls pattern instance."""
        return CustodyPattern(
            pattern_name="2-2-3-2-2-3-blended",
            cycle_start="2026-01-26",
            group="girls"
        )

    def test_pattern_configuration(self, boys_pattern, girls_pattern):
        """Pattern has correct configuration."""
        assert boys_pattern.cycle_days == 14
        assert girls_pattern.cycle_days == 14
        assert boys_pattern.cycle_start == date(2026, 1, 26)
        assert girls_pattern.cycle_start == date(2026, 1, 26)

    def test_user_specific_dates_boys(self, boys_pattern):
        """Boys pattern matches user's calendar."""
        # |G|G|B|B|B/G|B/G|B/G|G|G|B|B|Z|Z|Z|
        test_cases = [
            ("2026-01-26", False),  # Day 0: Girls only
            ("2026-01-27", False),  # Day 1: Girls only
            ("2026-01-28", True),   # Day 2: Boys only
            ("2026-01-29", True),   # Day 3: Boys only
            ("2026-01-30", True),   # Day 4: Both home
            ("2026-01-31", True),   # Day 5: Both home
            ("2026-02-01", True),   # Day 6: Both home
            ("2026-02-02", False),  # Day 7: Girls only
            ("2026-02-03", False),  # Day 8: Girls only
            ("2026-02-04", True),   # Day 9: Boys only
            ("2026-02-05", True),   # Day 10: Boys only
            ("2026-02-06", False),  # Day 11: Neither (boys away)
            ("2026-02-07", False),  # Day 12: Neither (boys away)
            ("2026-02-08", False),  # Day 13: Neither (boys away)
        ]

        errors = boys_pattern.validate_against_dates(test_cases)
        assert len(errors) == 0, f"Boys pattern errors: {errors}"

    def test_user_specific_dates_girls(self, girls_pattern):
        """Girls pattern matches user's calendar."""
        # |G|G|B|B|B/G|B/G|B/G|G|G|B|B|Z|Z|Z|
        test_cases = [
            ("2026-01-26", True),   # Day 0: Girls only
            ("2026-01-27", True),   # Day 1: Girls only
            ("2026-01-28", False),  # Day 2: Boys only
            ("2026-01-29", False),  # Day 3: Boys only
            ("2026-01-30", True),   # Day 4: Both home
            ("2026-01-31", True),   # Day 5: Both home
            ("2026-02-01", True),   # Day 6: Both home
            ("2026-02-02", True),   # Day 7: Girls only
            ("2026-02-03", True),   # Day 8: Girls only
            ("2026-02-04", False),  # Day 9: Boys only
            ("2026-02-05", False),  # Day 10: Boys only
            ("2026-02-06", False),  # Day 11: Neither (girls away)
            ("2026-02-07", False),  # Day 12: Neither (girls away)
            ("2026-02-08", False),  # Day 13: Neither (girls away)
        ]

        errors = girls_pattern.validate_against_dates(test_cases)
        assert len(errors) == 0, f"Girls pattern errors: {errors}"

    def test_both_home_days(self, boys_pattern, girls_pattern):
        """Days 4-6 have both groups home."""
        both_home_dates = [
            date(2026, 1, 30),  # Day 4: Thu
            date(2026, 1, 31),  # Day 5: Fri
            date(2026, 2, 1),   # Day 6: Sat
        ]

        for check_date in both_home_dates:
            assert boys_pattern.is_present(check_date), (
                f"Boys should be home on {check_date}"
            )
            assert girls_pattern.is_present(check_date), (
                f"Girls should be home on {check_date}"
            )

    def test_neither_home_days(self, boys_pattern, girls_pattern):
        """Days 11-13 have neither group home (parent respite)."""
        neither_home_dates = [
            date(2026, 2, 6),  # Day 11: Thu
            date(2026, 2, 7),  # Day 12: Fri
            date(2026, 2, 8),  # Day 13: Sat
        ]

        for check_date in neither_home_dates:
            assert not boys_pattern.is_present(check_date), (
                f"Boys should be away on {check_date}"
            )
            assert not girls_pattern.is_present(check_date), (
                f"Girls should be away on {check_date}"
            )

    def test_pattern_repeats_correctly(self, boys_pattern, girls_pattern):
        """Pattern repeats correctly after 14 days."""
        # Day 0 and Day 14 should match
        day_0 = date(2026, 1, 26)
        day_14 = date(2026, 2, 9)

        assert boys_pattern.is_present(day_0) == boys_pattern.is_present(day_14)
        assert girls_pattern.is_present(day_0) == girls_pattern.is_present(day_14)

        # Day 4 and Day 18 should match (both home)
        day_4 = date(2026, 1, 30)
        day_18 = date(2026, 2, 13)

        assert boys_pattern.is_present(day_4) == boys_pattern.is_present(day_18)
        assert girls_pattern.is_present(day_4) == girls_pattern.is_present(day_18)


class TestModuloArithmetic:
    """Test date calculation edge cases."""

    @pytest.fixture
    def pattern(self):
        """Test pattern instance."""
        return CustodyPattern(
            pattern_name="2-2-3",
            cycle_start="2026-01-05",
            group="boys"
        )

    def test_dates_after_anchor(self, pattern):
        """Dates after anchor work correctly."""
        # 7-day cycle, so day 7 should equal day 0
        day_0 = date(2026, 1, 5)
        day_7 = date(2026, 1, 12)

        assert pattern.is_present(day_0) == pattern.is_present(day_7)

    def test_dates_before_anchor(self, pattern):
        """Dates before anchor work correctly (negative modulo)."""
        # Day -1 should equal day 6 (last day of previous cycle)
        day_0 = date(2026, 1, 5)
        day_minus_1 = date(2026, 1, 4)

        # In 2-2-3 pattern: [T, T, F, F, T, T, T]
        # Day 0 = True, Day 6 = True
        assert pattern.is_present(day_0) is True
        assert pattern.is_present(day_minus_1) is True  # Should be day 6

    def test_far_future_date(self, pattern):
        """Dates far in the future work correctly."""
        # 1000 days in the future
        far_future = pattern.cycle_start + timedelta(days=1000)
        # Should still work with modulo arithmetic
        result = pattern.is_present(far_future)
        assert isinstance(result, bool)

    def test_leap_year_boundary(self):
        """Pattern works across leap year boundary."""
        # 2024 is a leap year
        pattern = CustodyPattern(
            pattern_name="2-2-3",
            cycle_start="2024-02-28",
            group="boys"
        )

        feb_28 = date(2024, 2, 28)
        feb_29 = date(2024, 2, 29)  # Leap day
        mar_1 = date(2024, 3, 1)

        # All dates should work
        assert isinstance(pattern.is_present(feb_28), bool)
        assert isinstance(pattern.is_present(feb_29), bool)
        assert isinstance(pattern.is_present(mar_1), bool)


class TestGetStatus:
    """Test get_status method."""

    @pytest.fixture
    def pattern(self):
        """Test pattern instance."""
        return CustodyPattern(
            pattern_name="2-2-3-2-2-3-blended",
            cycle_start="2026-01-26",
            group="boys"
        )

    def test_get_status_home(self, pattern):
        """Returns HOME when present."""
        check_date = date(2026, 1, 28)  # Day 2: Boys home
        assert pattern.get_status(check_date) == "HOME"

    def test_get_status_away(self, pattern):
        """Returns AWAY when not present."""
        check_date = date(2026, 1, 26)  # Day 0: Boys away
        assert pattern.get_status(check_date) == "AWAY"


class TestVisualization:
    """Test visualization methods."""

    def test_visualize_single_pattern(self):
        """Visualize single pattern."""
        pattern = CustodyPattern(
            pattern_name="2-2-3",
            cycle_start="2026-01-05",
            group="boys"
        )

        output = pattern.visualize()

        assert "Pattern: 2-2-3 (boys)" in output
        assert "Cycle: 7 days" in output
        assert "Anchor: 2026-01-05" in output
        # Check for presence markers
        assert "X" in output

    def test_visualize_both_groups(self):
        """Visualize both groups side-by-side."""
        output = visualize_both_groups(
            "2-2-3-2-2-3-blended",
            "2026-01-26",
            num_days=14
        )

        assert "Pattern: 2-2-3-2-2-3-blended" in output
        assert "Anchor: 2026-01-26" in output
        assert "Boys" in output
        assert "Girls" in output
        assert "State" in output

        # Check for state labels
        assert "G" in output  # Girls only
        assert "B" in output  # Boys only
        assert "B/G" in output  # Both
        assert "Z" in output  # Neither

    def test_visualize_multiple_cycles(self):
        """Visualize multiple cycles."""
        pattern = CustodyPattern(
            pattern_name="2-2-3",
            cycle_start="2026-01-05",
            group="boys"
        )

        output = pattern.visualize(num_cycles=2)

        # Should show 14 days for 2 cycles of 7-day pattern
        # Count day number headers
        assert "|13|" in output or "| 13|" in output


class TestStandardPatterns:
    """Test standard patterns from library."""

    @pytest.mark.parametrize("pattern_name", [
        "2-5-5-2",
        "3-4-4-3",
        "2-2-3",
        "2-2-5-5",
        "week-on-week-off",
        "every-other-weekend",
    ])
    def test_standard_pattern_initializes(self, pattern_name):
        """Standard pattern initializes without errors."""
        boys = CustodyPattern(
            pattern_name=pattern_name,
            cycle_start="2026-01-05",
            group="boys"
        )
        girls = CustodyPattern(
            pattern_name=pattern_name,
            cycle_start="2026-01-05",
            group="girls"
        )

        assert boys.cycle_days > 0
        assert girls.cycle_days > 0
        assert len(boys.pattern_array) == boys.cycle_days
        assert len(girls.pattern_array) == girls.cycle_days

    def test_week_on_week_off_pattern(self):
        """Week-on-week-off pattern works correctly."""
        pattern = CustodyPattern(
            pattern_name="week-on-week-off",
            cycle_start="2026-01-05",  # Monday
            group="boys"
        )

        # First week should be home
        for i in range(7):
            check_date = date(2026, 1, 5) + timedelta(days=i)
            assert pattern.is_present(check_date) is True

        # Second week should be away
        for i in range(7, 14):
            check_date = date(2026, 1, 5) + timedelta(days=i)
            assert pattern.is_present(check_date) is False


class TestValidateAgainstDates:
    """Test validate_against_dates method."""

    def test_validate_all_pass(self):
        """All test cases pass validation."""
        pattern = CustodyPattern(
            pattern_name="2-2-3",
            cycle_start="2026-01-05",
            group="boys"
        )

        # 2-2-3 pattern: [T, T, F, F, T, T, T]
        test_cases = [
            ("2026-01-05", True),   # Day 0
            ("2026-01-06", True),   # Day 1
            ("2026-01-07", False),  # Day 2
            ("2026-01-08", False),  # Day 3
            ("2026-01-09", True),   # Day 4
        ]

        errors = pattern.validate_against_dates(test_cases)
        assert len(errors) == 0

    def test_validate_with_errors(self):
        """Validation detects mismatches."""
        pattern = CustodyPattern(
            pattern_name="2-2-3",
            cycle_start="2026-01-05",
            group="boys"
        )

        # Intentionally wrong expectations
        test_cases = [
            ("2026-01-05", False),  # Should be True
            ("2026-01-07", True),   # Should be False
        ]

        errors = pattern.validate_against_dates(test_cases)
        assert len(errors) == 2
        assert "2026-01-05" in errors[0]
        assert "2026-01-07" in errors[1]
