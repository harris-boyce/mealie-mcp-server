"""Custody schedule pattern library and configuration.

This module provides a pattern-based approach to custody scheduling, replacing
event-based calendar parsing with simple boolean array indexing.
"""

from datetime import date
from typing import Dict, List, Literal, Optional


# Common custody patterns (14-day or 7-day cycles)
# Each pattern: {"boys": [...], "girls": [...]} where True = present
CUSTODY_PATTERNS = {
    "2-5-5-2": {
        "description": "2 days A, 5 days B, 5 days A, 2 days B",
        "cycle_days": 14,
        "boys": [
            True, True,        # Days 0-1: First 2 days
            False, False, False, False, False,  # Days 2-6: 5 days away
            True, True, True, True, True,       # Days 7-11: 5 days home
            False, False       # Days 12-13: 2 days away
        ],
        "girls": [
            True, True,        # Same pattern for girls
            False, False, False, False, False,
            True, True, True, True, True,
            False, False
        ],
    },
    "3-4-4-3": {
        "description": "3 days A, 4 days B, 4 days A, 3 days B",
        "cycle_days": 14,
        "boys": [
            True, True, True,           # Days 0-2: 3 days
            False, False, False, False, # Days 3-6: 4 days away
            True, True, True, True,     # Days 7-10: 4 days home
            False, False, False         # Days 11-13: 3 days away
        ],
        "girls": [
            True, True, True,
            False, False, False, False,
            True, True, True, True,
            False, False, False
        ],
    },
    "2-2-3": {
        "description": "2 days A, 2 days B, 3 days A (repeats weekly)",
        "cycle_days": 7,
        "boys": [
            True, True,          # Days 0-1: 2 days
            False, False,        # Days 2-3: 2 days away
            True, True, True     # Days 4-6: 3 days
        ],
        "girls": [
            True, True,
            False, False,
            True, True, True
        ],
    },
    "2-2-5-5": {
        "description": "2 days A, 2 days B, 5 days A, 5 days B",
        "cycle_days": 14,
        "boys": [
            True, True,                    # Days 0-1: 2 days
            False, False,                  # Days 2-3: 2 days away
            True, True, True, True, True,  # Days 4-8: 5 days
            False, False, False, False, False  # Days 9-13: 5 days away
        ],
        "girls": [
            True, True,
            False, False,
            True, True, True, True, True,
            False, False, False, False, False
        ],
    },
    "week-on-week-off": {
        "description": "7 days A, 7 days B (alternating weeks)",
        "cycle_days": 14,
        "boys": [
            True, True, True, True, True, True, True,      # Week 1
            False, False, False, False, False, False, False  # Week 2
        ],
        "girls": [
            True, True, True, True, True, True, True,
            False, False, False, False, False, False, False
        ],
    },
    "every-other-weekend": {
        "description": "Weekdays with parent A, alternating weekends",
        "cycle_days": 14,
        # Mon-Thu A, Fri-Sun B, Mon-Thu A, Fri-Sun A
        "boys": [
            True, True, True, True,           # Mon-Thu week 1
            False, False, False,              # Fri-Sun week 1 (away)
            True, True, True, True,           # Mon-Thu week 2
            True, True, True                  # Fri-Sun week 2 (home)
        ],
        "girls": [
            True, True, True, True,
            False, False, False,
            True, True, True, True,
            True, True, True
        ],
    },
    "2-2-3-2-2-3-blended": {
        "description": "Custom blended: 2-2-3 alternating, 3-day weekend together, 3-day parent break",
        "cycle_days": 14,
        "boys": [
            False, False,  # Days 0-1: Girls only (Sun-Mon)
            True, True,    # Days 2-3: Boys only (Tue-Wed)
            True, True, True,  # Days 4-6: Both together (Thu-Sat)
            False, False,  # Days 7-8: Girls only (Sun-Mon)
            True, True,    # Days 9-10: Boys only (Tue-Wed)
            False, False, False  # Days 11-13: Neither - parent respite (Thu-Sat)
        ],
        "girls": [
            True, True,    # Days 0-1: Girls only (Sun-Mon)
            False, False,  # Days 2-3: Boys only (Tue-Wed)
            True, True, True,  # Days 4-6: Both together (Thu-Sat)
            True, True,    # Days 7-8: Girls only (Sun-Mon)
            False, False,  # Days 9-10: Boys only (Tue-Wed)
            False, False, False  # Days 11-13: Neither - parent respite (Thu-Sat)
        ],
    },
}


class CustodyPattern:
    """Custody schedule pattern calculator for a single group."""

    def __init__(
        self,
        pattern_name: Optional[str] = None,
        cycle_start: str = "2026-01-05",
        custom_pattern: Optional[Dict] = None,
        group: Literal["boys", "girls"] = "boys"
    ):
        """
        Initialize custody pattern for a specific group.

        Args:
            pattern_name: Name from CUSTODY_PATTERNS library
            cycle_start: Anchor date for cycle (YYYY-MM-DD)
            custom_pattern: Override with custom pattern dict
            group: Which group this pattern is for ("boys" or "girls")

        Raises:
            ValueError: If neither pattern_name nor custom_pattern provided,
                       or if pattern is invalid

        Examples:
            >>> boys = CustodyPattern("2-2-3-2-2-3-blended", "2026-01-26", group="boys")
            >>> girls = CustodyPattern("2-2-3-2-2-3-blended", "2026-01-26", group="girls")
            >>> boys.is_present(date(2026, 1, 30))  # Day 4: Both home
            True
            >>> girls.is_present(date(2026, 1, 30))  # Day 4: Both home
            True
        """
        self.group = group

        # Load pattern configuration
        if custom_pattern:
            self.pattern_config = custom_pattern
            self.pattern_name = custom_pattern.get("description", "Custom")
        elif pattern_name and pattern_name in CUSTODY_PATTERNS:
            self.pattern_config = CUSTODY_PATTERNS[pattern_name]
            self.pattern_name = pattern_name
        else:
            available = list(CUSTODY_PATTERNS.keys())
            raise ValueError(
                f"Must provide either pattern_name from {available} "
                f"or custom_pattern dict"
            )

        # Parse anchor date
        self.cycle_start = date.fromisoformat(cycle_start)
        self.cycle_days = self.pattern_config["cycle_days"]

        # Extract pattern array for this group
        if group not in self.pattern_config:
            raise ValueError(
                f"Pattern missing '{group}' key. Available keys: "
                f"{list(self.pattern_config.keys())}"
            )

        self.pattern_array = self.pattern_config[group]

        # Validate pattern
        if len(self.pattern_array) != self.cycle_days:
            raise ValueError(
                f"Pattern array length {len(self.pattern_array)} != "
                f"cycle_days {self.cycle_days}"
            )

    def is_present(self, check_date: date) -> bool:
        """
        Check if group is present on given date based on pattern.

        Args:
            check_date: Date to check

        Returns:
            True if group is present, False otherwise

        Examples:
            >>> pattern = CustodyPattern("2-2-3-2-2-3-blended", "2026-01-26", group="boys")
            >>> pattern.is_present(date(2026, 1, 26))  # Day 0: Girls only
            False
            >>> pattern.is_present(date(2026, 1, 30))  # Day 4: Both home
            True
        """
        days_since_anchor = (check_date - self.cycle_start).days
        cycle_day = days_since_anchor % self.cycle_days
        return self.pattern_array[cycle_day]

    def get_status(self, check_date: date) -> str:
        """
        Get custody status for this group on given date.

        Args:
            check_date: Date to check

        Returns:
            "HOME" if present, "AWAY" if not

        Examples:
            >>> pattern = CustodyPattern("2-2-3-2-2-3-blended", "2026-01-26", group="girls")
            >>> pattern.get_status(date(2026, 1, 26))
            'HOME'
        """
        return "HOME" if self.is_present(check_date) else "AWAY"

    def visualize(self, num_cycles: int = 1) -> str:
        """
        Generate visual representation of pattern.

        Args:
            num_cycles: Number of cycles to display (default: 1)

        Returns:
            Multi-line string showing pattern grid

        Examples:
            >>> pattern = CustodyPattern("2-2-3", "2026-01-05", group="boys")
            >>> print(pattern.visualize())
            Pattern: 2-2-3 (boys)
            Cycle: 7 days
            Anchor: 2026-01-05
            <BLANKLINE>
            | 0| 1| 2| 3| 4| 5| 6|
            ----------------------
            | X| X|  |  | X| X| X|
        """
        lines = []
        lines.append(f"Pattern: {self.pattern_name} ({self.group})")
        lines.append(f"Cycle: {self.cycle_days} days")
        lines.append(f"Anchor: {self.cycle_start.isoformat()}")
        lines.append("")

        # Repeat pattern for multiple cycles
        extended_pattern = self.pattern_array * num_cycles
        total_days = len(extended_pattern)

        # Header with day numbers
        header = "|" + "|".join(f"{i:2d}" for i in range(total_days)) + "|"
        lines.append(header)
        lines.append("-" * len(header))

        # Pattern row
        pattern_row = "|" + "|".join(" X" if p else "  " for p in extended_pattern) + "|"
        lines.append(pattern_row)

        return "\n".join(lines)

    def validate_against_dates(
        self,
        test_cases: List[tuple[str, bool]]
    ) -> List[str]:
        """
        Validate pattern against expected dates.

        Args:
            test_cases: List of (date_string, expected_present) tuples

        Returns:
            List of error messages (empty if all pass)

        Examples:
            >>> pattern = CustodyPattern("2-2-3-2-2-3-blended", "2026-01-26", group="boys")
            >>> test_cases = [
            ...     ("2026-01-26", False),  # Day 0: Girls only
            ...     ("2026-01-28", True),   # Day 2: Boys only
            ... ]
            >>> errors = pattern.validate_against_dates(test_cases)
            >>> len(errors)
            0
        """
        errors = []
        for date_str, expected in test_cases:
            check = date.fromisoformat(date_str)
            actual = self.is_present(check)
            if actual != expected:
                errors.append(
                    f"{date_str}: Expected {expected}, got {actual}"
                )
        return errors


def visualize_both_groups(
    pattern_name: str,
    cycle_start: str,
    num_days: int = 14
) -> str:
    """
    Visualize custody pattern for both boys and girls side-by-side.

    Args:
        pattern_name: Pattern name from CUSTODY_PATTERNS library
        cycle_start: Anchor date (YYYY-MM-DD)
        num_days: Number of days to display (default: 14)

    Returns:
        Multi-line string showing both groups' patterns

    Examples:
        >>> print(visualize_both_groups("2-2-3-2-2-3-blended", "2026-01-26", 14))
        Pattern: 2-2-3-2-2-3-blended
        Anchor: 2026-01-26
        Cycle: 14 days
        <BLANKLINE>
        Day  | 0| 1| 2| 3| 4| 5| 6| 7| 8| 9|10|11|12|13|
        -----+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
        Boys |  |  | X| X| X| X| X|  |  | X| X|  |  |  |
        Girls| X| X|  |  | X| X| X| X| X|  |  |  |  |  |
        State| G| G| B| B|B/G|B/G|B/G| G| G| B| B| Z| Z| Z|
    """
    boys = CustodyPattern(pattern_name, cycle_start, group="boys")
    girls = CustodyPattern(pattern_name, cycle_start, group="girls")

    pattern_config = CUSTODY_PATTERNS[pattern_name]

    lines = []
    lines.append(f"Pattern: {pattern_name}")
    lines.append(f"Anchor: {cycle_start}")
    lines.append(f"Cycle: {pattern_config['cycle_days']} days")
    lines.append("")

    # Header
    header = "Day  |" + "|".join(f"{i:2d}" for i in range(num_days)) + "|"
    lines.append(header)
    lines.append("-----+" + "+".join("--" for _ in range(num_days)) + "+")

    # Boys row
    boys_row = "Boys |" + "|".join(
        " X" if boys.pattern_array[i % boys.cycle_days] else "  "
        for i in range(num_days)
    ) + "|"
    lines.append(boys_row)

    # Girls row
    girls_row = "Girls|" + "|".join(
        " X" if girls.pattern_array[i % girls.cycle_days] else "  "
        for i in range(num_days)
    ) + "|"
    lines.append(girls_row)

    # State row (G, B, B/G, Z)
    state_row = "State|" + "|".join(
        _get_state_label(
            boys.pattern_array[i % boys.cycle_days],
            girls.pattern_array[i % girls.cycle_days]
        )
        for i in range(num_days)
    ) + "|"
    lines.append(state_row)

    return "\n".join(lines)


def _get_state_label(boys_home: bool, girls_home: bool) -> str:
    """Get state label for visualization."""
    if boys_home and girls_home:
        return "B/G"
    elif boys_home:
        return " B"
    elif girls_home:
        return " G"
    else:
        return " Z"
