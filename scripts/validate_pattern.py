#!/usr/bin/env python3
"""
Custody pattern validation script.

This script validates the configured custody pattern against known dates
and visualizes the pattern for easy verification.

Usage:
    python scripts/validate_pattern.py
"""

import sys
from pathlib import Path
from datetime import date, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.custody_patterns import CustodyPattern, visualize_both_groups


def main():
    """Run pattern validation."""
    print("=" * 80)
    print("CUSTODY PATTERN VALIDATION")
    print("=" * 80)
    print()

    # Configuration
    pattern_name = "2-2-3-2-2-3-blended"
    anchor_date = "2026-01-26"

    print(f"Pattern: {pattern_name}")
    print(f"Anchor: {anchor_date}")
    print()

    # Create pattern instances
    boys = CustodyPattern(pattern_name, anchor_date, group="boys")
    girls = CustodyPattern(pattern_name, anchor_date, group="girls")

    # Visualize pattern grid
    print("=" * 80)
    print("PATTERN VISUALIZATION (Both Groups)")
    print("=" * 80)
    print()
    print(visualize_both_groups(pattern_name, anchor_date, num_days=14))
    print()

    # User's specific test cases from calendar: |G|G|B|B|B/G|B/G|B/G|G|G|B|B|Z|Z|Z|
    print("=" * 80)
    print("VALIDATION: User's Specific Dates (Jan 26 - Feb 8, 2026)")
    print("=" * 80)
    print()

    test_cases = [
        (date(2026, 1, 26), False, True, "Girls only"),   # Day 0
        (date(2026, 1, 27), False, True, "Girls only"),   # Day 1
        (date(2026, 1, 28), True, False, "Boys only"),    # Day 2
        (date(2026, 1, 29), True, False, "Boys only"),    # Day 3
        (date(2026, 1, 30), True, True, "Both together"), # Day 4
        (date(2026, 1, 31), True, True, "Both together"), # Day 5
        (date(2026, 2, 1), True, True, "Both together"),  # Day 6
        (date(2026, 2, 2), False, True, "Girls only"),    # Day 7
        (date(2026, 2, 3), False, True, "Girls only"),    # Day 8
        (date(2026, 2, 4), True, False, "Boys only"),     # Day 9
        (date(2026, 2, 5), True, False, "Boys only"),     # Day 10
        (date(2026, 2, 6), False, False, "Neither (parent respite)"), # Day 11
        (date(2026, 2, 7), False, False, "Neither (parent respite)"), # Day 12
        (date(2026, 2, 8), False, False, "Neither (parent respite)"), # Day 13
    ]

    all_pass = True
    for check_date, expected_boys, expected_girls, description in test_cases:
        actual_boys = boys.is_present(check_date)
        actual_girls = girls.is_present(check_date)

        # Determine state
        if actual_boys and actual_girls:
            state = "B/G"
        elif actual_boys:
            state = "B  "
        elif actual_girls:
            state = "G  "
        else:
            state = "Z  "

        # Check if matches expected
        boys_match = actual_boys == expected_boys
        girls_match = actual_girls == expected_girls
        match = boys_match and girls_match

        status = "✓" if match else "✗"

        print(f"{status} {check_date.strftime('%Y-%m-%d %a')} | {state} | {description}")

        if not match:
            all_pass = False
            print(f"   ERROR: Expected boys={expected_boys}, girls={expected_girls}")
            print(f"          Got boys={actual_boys}, girls={actual_girls}")

    print()

    if all_pass:
        print("✓ All validation checks passed!")
    else:
        print("✗ Some validation checks failed - pattern configuration needs adjustment")
        sys.exit(1)

    # Extended calendar view for next 30 days
    print()
    print("=" * 80)
    print("EXTENDED CALENDAR VIEW (Next 42 days for verification)")
    print("=" * 80)
    print()
    print("Date       | Day | Boys | Girls | State | Description")
    print("-----------+-----+------+-------+-------+-----------------------------------")

    start = date.fromisoformat(anchor_date)
    for i in range(42):  # 3 full cycles
        current = start + timedelta(days=i)
        boys_home = boys.is_present(current)
        girls_home = girls.is_present(current)

        if boys_home and girls_home:
            state = "B/G"
            desc = "Both kids home - full family meals"
        elif boys_home:
            state = " B "
            desc = "Boys home, girls away"
        elif girls_home:
            state = " G "
            desc = "Girls home, boys away"
        else:
            state = " Z "
            desc = "No kids home - parent respite or adults only"

        cycle_day = i % boys.cycle_days

        print(
            f"{current.isoformat()} | {current.strftime('%a')} | "
            f"{'✓' if boys_home else '✗':^4} | {'✓' if girls_home else '✗':^5} | "
            f"{state} | {desc} (cycle day {cycle_day})"
        )

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Pattern: {boys.pattern_config['description']}")
    print(f"Cycle: {boys.cycle_days} days")
    print(f"Anchor: {anchor_date}")
    print()

    # Count days by state in one cycle
    both_count = sum(
        1 for i in range(boys.cycle_days)
        if boys.pattern_array[i] and girls.pattern_array[i]
    )
    boys_only_count = sum(
        1 for i in range(boys.cycle_days)
        if boys.pattern_array[i] and not girls.pattern_array[i]
    )
    girls_only_count = sum(
        1 for i in range(boys.cycle_days)
        if not boys.pattern_array[i] and girls.pattern_array[i]
    )
    neither_count = sum(
        1 for i in range(boys.cycle_days)
        if not boys.pattern_array[i] and not girls.pattern_array[i]
    )

    print(f"Per cycle ({boys.cycle_days} days):")
    print(f"  - Both home: {both_count} days")
    print(f"  - Boys only: {boys_only_count} days")
    print(f"  - Girls only: {girls_only_count} days")
    print(f"  - Neither home: {neither_count} days")
    print()

    if all_pass:
        print("✓ Pattern validation complete - configuration is correct!")
        return 0
    else:
        print("✗ Pattern validation failed - please review configuration")
        return 1


if __name__ == "__main__":
    sys.exit(main())
