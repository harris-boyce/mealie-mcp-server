# Pattern-Based Custody Schedule Refactoring Specification

## Overview

Refactor the meal planning MCP server from calendar-event-based custody tracking to a pattern-based boolean array system. This reduces complexity by ~75% while improving clarity and maintainability.

## Goals

1. **Simplify custody determination**: Replace event parsing/merging with simple array indexing
2. **Reduce code complexity**: Eliminate ~250 lines of datetime parsing and interval merging
3. **Improve user understanding**: Visual pattern representation is self-documenting
4. **Maintain flexibility**: Support common custody patterns and blended families
5. **Keep activity complexity**: Activity calendars still drive meal complexity classification

## Architecture Changes

### Before (Event-Based)
```
┌─────────────────────────────────────┐
│  Fetch 2 custody calendars          │
│  - boys_custody_schedule            │
│  - girls_custody_schedule           │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  Parse event datetimes              │
│  - Handle ISO strings               │
│  - Handle date dicts                │
│  - Handle datetime dicts            │
│  - Normalize timezones              │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  Merge overlapping intervals        │
│  - Sort by start time               │
│  - Detect overlaps/contiguous       │
│  - Merge into ON periods            │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  Calculate FULL_ON/PARTIAL_ON/OFF   │
│  - Compare interval to day bounds   │
│  - Determine start/end times        │
└─────────────────────────────────────┘
```

### After (Pattern-Based)
```
┌─────────────────────────────────────┐
│  Pattern Configuration              │
│  - Boolean array (14 or 7 days)     │
│  - Cycle anchor date                │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  Simple Calculation                 │
│  days_since_anchor % cycle_days     │
│  → array[index] = True/False        │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  Apply exceptions if present        │
│  (from single exception calendar)   │
└─────────────────────────────────────┘
```

## File Changes

### 1. New File: `utils/custody_patterns.py`

Create new file defining pattern library and calculator:

```python
"""Custody schedule pattern library and configuration."""

from datetime import date
from typing import Dict, List, Literal, Optional

# Common custody patterns (14-day or 7-day cycles)
# Each pattern: [boys_schedule, girls_schedule] where True = present
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
}


class CustodyPattern:
    """Custody schedule pattern calculator."""
    
    def __init__(
        self,
        pattern_name: Optional[str] = None,
        cycle_start: str = "2026-01-05",
        custom_pattern: Optional[Dict] = None
    ):
        """
        Initialize custody pattern.
        
        Args:
            pattern_name: Name from CUSTODY_PATTERNS library (optional if custom_pattern provided)
            cycle_start: Anchor date for cycle (YYYY-MM-DD)
            custom_pattern: Override with custom pattern dict (for blended families)
        
        Raises:
            ValueError: If neither pattern_name nor custom_pattern provided, or pattern unknown
        """
        if custom_pattern:
            self.pattern = custom_pattern
        elif pattern_name and pattern_name in CUSTODY_PATTERNS:
            self.pattern = CUSTODY_PATTERNS[pattern_name]
        else:
            raise ValueError(
                f"Must provide either pattern_name from {list(CUSTODY_PATTERNS.keys())} "
                f"or custom_pattern dict"
            )
        
        self.cycle_start = date.fromisoformat(cycle_start)
        self.cycle_days = self.pattern["cycle_days"]
        
        # Validate pattern
        if len(self.pattern["boys"]) != self.cycle_days:
            raise ValueError(f"Boys pattern length {len(self.pattern['boys'])} != cycle_days {self.cycle_days}")
        if len(self.pattern["girls"]) != self.cycle_days:
            raise ValueError(f"Girls pattern length {len(self.pattern['girls'])} != cycle_days {self.cycle_days}")
    
    def is_present(self, check_date: date, group: Literal["boys", "girls"]) -> bool:
        """
        Check if group is present on given date based on pattern.
        
        Args:
            check_date: Date to check
            group: "boys" or "girls"
        
        Returns:
            True if group is present, False otherwise
        """
        days_since_anchor = (check_date - self.cycle_start).days
        cycle_day = days_since_anchor % self.cycle_days
        return self.pattern[group][cycle_day]
    
    def get_status(self, check_date: date) -> Dict[str, bool]:
        """
        Get custody status for both groups.
        
        Args:
            check_date: Date to check
        
        Returns:
            Dict with "boys" and "girls" boolean presence
        """
        return {
            "boys": self.is_present(check_date, "boys"),
            "girls": self.is_present(check_date, "girls"),
        }
    
    def visualize(self) -> str:
        """
        Generate visual representation of pattern.
        
        Returns:
            Multi-line string showing pattern grid
        """
        lines = []
        lines.append(f"Pattern: {self.pattern.get('description', 'Custom')}")
        lines.append(f"Cycle: {self.cycle_days} days")
        lines.append(f"Anchor: {self.cycle_start.isoformat()}")
        lines.append("")
        
        # Header with day numbers
        header = "|" + "|".join(f"{i:2d}" for i in range(self.cycle_days)) + "|"
        lines.append(header)
        lines.append("-" * len(header))
        
        # Boys row
        boys_row = "|" + "|".join(" X" if p else "  " for p in self.pattern["boys"]) + "|"
        lines.append(f"Boys  {boys_row}")
        
        # Girls row
        girls_row = "|" + "|".join(" X" if p else "  " for p in self.pattern["girls"]) + "|"
        lines.append(f"Girls {girls_row}")
        
        return "\n".join(lines)


# Example blended family pattern (different schedules)
BLENDED_FAMILY_EXAMPLE = {
    "description": "Boys 2-5-5-2, Girls week-on-week-off",
    "cycle_days": 14,
    "boys": [
        True, True,
        False, False, False, False, False,
        True, True, True, True, True,
        False, False
    ],
    "girls": [
        True, True, True, True, True, True, True,
        False, False, False, False, False, False, False
    ],
}
```

**Validation Tests:**

```python
def test_pattern_validation():
    """Test pattern configuration."""
    schedule = CustodyPattern(
        pattern_name="2-5-5-2",
        cycle_start="2026-01-05"
    )
    
    print(schedule.visualize())
    
    # Test specific dates
    test_dates = [
        date(2026, 1, 5),   # Day 0 of cycle
        date(2026, 1, 6),   # Day 1 of cycle
        date(2026, 1, 7),   # Day 2 of cycle (should be False)
        date(2026, 1, 12),  # Day 7 of cycle (should be True)
    ]
    
    for d in test_dates:
        status = schedule.get_status(d)
        print(f"{d}: {status}")
```

### 2. Modify: `utils/calendar_parser.py`

**Remove these functions (no longer needed):**
- `parse_event_datetime()` - only needed for activities now, move to simpler version
- `normalize_all_day_event()` - not needed
- `merge_overlapping_intervals()` - not needed
- `get_day_status()` - replaced by pattern.is_present()

**Keep/Simplify these functions:**
- `get_activities_for_day()` - still needed for activity complexity
- `classify_day_complexity()` - still needed

**New simplified version:**

```python
"""Simplified calendar parsing for activities only."""

from datetime import datetime, date, timedelta
from typing import Any, Dict, List
from zoneinfo import ZoneInfo


def parse_activity_datetime(dt_value: Any, default_tz: str = "America/New_York") -> datetime:
    """
    Parse activity event datetime (simplified version).
    
    Args:
        dt_value: ISO string or dict with dateTime/date
        default_tz: Default timezone if not specified
    
    Returns:
        Timezone-aware datetime
    """
    if isinstance(dt_value, str):
        if "T" in dt_value:
            return datetime.fromisoformat(dt_value)
        # Date string - set to start of day
        d = date.fromisoformat(dt_value)
        return datetime.combine(d, datetime.min.time()).replace(
            tzinfo=ZoneInfo(default_tz)
        )
    
    if isinstance(dt_value, dict):
        if "dateTime" in dt_value:
            return datetime.fromisoformat(dt_value["dateTime"])
        if "date" in dt_value:
            d = date.fromisoformat(dt_value["date"])
            return datetime.combine(d, datetime.min.time()).replace(
                tzinfo=ZoneInfo(default_tz)
            )
    
    raise ValueError(f"Cannot parse datetime: {dt_value}")


def get_activities_for_day(
    day: date,
    events: List[Dict[str, Any]],
    tz: ZoneInfo
) -> List[Dict[str, Any]]:
    """
    Get all activity events that occur on a specific day.
    
    Args:
        day: Date to check
        events: List of activity events
        tz: Timezone
    
    Returns:
        List of activities for this day
    """
    day_start = datetime.combine(day, datetime.min.time()).replace(tzinfo=tz)
    day_end = datetime.combine(day, datetime.max.time()).replace(tzinfo=tz)
    
    activities = []
    for event in events:
        start = parse_activity_datetime(event["start"])
        end = parse_activity_datetime(event["end"])
        
        # Check if event overlaps this day
        if start < day_end and end > day_start:
            activities.append({
                "summary": event.get("summary", ""),
                "start": start.isoformat(),
                "end": end.isoformat(),
                "location": event.get("location", ""),
                "description": event.get("description", ""),
            })
    
    return activities


def classify_day_complexity(
    activities: List[Dict[str, Any]],
    tz: ZoneInfo
) -> str:
    """
    Classify day complexity based on activities.
    
    Rules:
    - 3+ activities OR 2+ late activities (after 6pm) → CHAOTIC
    - 2 activities OR 1 late activity → BUSY
    - 1 activity → MODERATE
    - 0 activities → CALM
    
    Args:
        activities: List of activity events for the day
        tz: Timezone
    
    Returns:
        Complexity label: CALM, MODERATE, BUSY, CHAOTIC
    """
    if not activities:
        return "CALM"
    
    count = len(activities)
    
    # Count late activities (6pm or later)
    late_count = sum(
        1 for activity in activities
        if parse_activity_datetime(activity["start"]).hour >= 18
    )
    
    # Classification
    if count >= 3 or late_count >= 2:
        return "CHAOTIC"
    elif count == 2 or late_count == 1:
        return "BUSY"
    elif count == 1:
        return "MODERATE"
    else:
        return "CALM"
```

### 3. Modify: `tools/meal_planning_context.py`

Replace entire file with simplified pattern-based version:

```python
"""Meal planning context tool with pattern-based custody schedules."""

import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from utils.custody_patterns import CustodyPattern
from utils.calendar_parser import (
    get_activities_for_day,
    classify_day_complexity,
)


async def get_meal_planning_context(
    client,  # HomeAssistantFetcher instance
    start_date: str,
    end_date: str,
    tz: str = "America/New_York",
    custody_pattern: str = None,
    cycle_start: str = None,
) -> Dict[str, Any]:
    """
    Get unified meal planning context using pattern-based custody schedules.
    
    Fetches activity calendars and combines with pattern-based custody
    to produce per-day context with:
    - Presence status (boys/girls home/away from pattern)
    - Activity list (events that impact meal complexity)
    - Complexity classification (CALM, MODERATE, BUSY, CHAOTIC)
    
    Args:
        client: HomeAssistantFetcher with calendar methods
        start_date: ISO date string (YYYY-MM-DD)
        end_date: ISO date string (YYYY-MM-DD)
        tz: Timezone string (default: America/New_York)
        custody_pattern: Pattern name (overrides env var)
        cycle_start: Cycle anchor date (overrides env var)
    
    Returns:
        Dict with:
            - date_range: {start, end, timezone}
            - pattern_info: {name, cycle_days, anchor}
            - combined: [...] per-day unified context for meal planning
    """
    timezone = ZoneInfo(tz)
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    
    # Initialize custody pattern from config or parameters
    pattern_name = custody_pattern or os.getenv("CUSTODY_PATTERN", "2-5-5-2")
    anchor_date = cycle_start or os.getenv("CUSTODY_CYCLE_START", "2026-01-05")
    
    schedule = CustodyPattern(
        pattern_name=pattern_name,
        cycle_start=anchor_date
    )
    
    # Calculate days ahead from now
    days_ahead = (end - date.today()).days
    
    # Fetch activity calendars only (no custody calendars needed!)
    benci_boys_response = await client.get_calendar_events_by_name(
        "benci_boys", 
        days_ahead=days_ahead
    )
    boycivengas_response = await client.get_calendar_events_by_name(
        "boycivengas", 
        days_ahead=days_ahead
    )
    
    # Optional: Fetch exception calendar if it exists
    # This allows overriding pattern for swaps/vacations
    exception_events = []
    try:
        exception_response = await client.get_calendar_events_by_name(
            "custody_exceptions",
            days_ahead=days_ahead
        )
        exception_events = [event.model_dump() for event in exception_response]
    except Exception:
        # Exception calendar is optional
        pass
    
    # Convert to dicts for processing
    benci_boys_events = [event.model_dump() for event in benci_boys_response]
    boycivengas_events = [event.model_dump() for event in boycivengas_response]
    
    # Build per-day context
    combined_days = []
    current = start
    
    while current <= end:
        # Get custody status from pattern
        pattern_status = schedule.get_status(current)
        
        # Check for exceptions that override pattern
        exceptions = _parse_exceptions_for_day(current, exception_events, timezone)
        boys_home = exceptions.get("boys", pattern_status["boys"])
        girls_home = exceptions.get("girls", pattern_status["girls"])
        
        # Get activities for the day
        benci_activities = get_activities_for_day(
            current, benci_boys_events, timezone
        )
        boycivengas_activities = get_activities_for_day(
            current, boycivengas_events, timezone
        )
        all_activities = benci_activities + boycivengas_activities
        
        # Classify complexity
        complexity = classify_day_complexity(all_activities, timezone)
        
        # Build combined day context
        day_context = {
            "date": current.isoformat(),
            "day_of_week": current.strftime("%A"),
            "custody": {
                "boys": "HOME" if boys_home else "AWAY",
                "girls": "HOME" if girls_home else "AWAY",
                "from_exception": current.isoformat() in exceptions.get("_dates", []),
            },
            "activities": {
                "benci_boys": benci_activities,
                "boycivengas": boycivengas_activities,
                "count": len(all_activities),
            },
            "complexity": complexity,
            "meal_planning_guidance": _get_meal_guidance(
                boys_home, girls_home, complexity
            ),
        }
        
        combined_days.append(day_context)
        current += timedelta(days=1)
    
    return {
        "date_range": {
            "start": start_date,
            "end": end_date,
            "timezone": tz,
        },
        "pattern_info": {
            "name": pattern_name,
            "description": schedule.pattern.get("description", "Custom"),
            "cycle_days": schedule.cycle_days,
            "cycle_start": anchor_date,
        },
        "combined": combined_days,
    }


def _parse_exceptions_for_day(
    check_date: date,
    events: List[Dict[str, Any]],
    tz: ZoneInfo
) -> Dict[str, Any]:
    """
    Parse exception calendar events for this day.
    
    Exception event summaries should contain:
    - "boys" or "girls" to indicate which group
    - "away" or "mom" or similar to indicate override to AWAY
    - "home" or "dad" or similar to indicate override to HOME
    
    Example events:
    - "Boys with mom" → boys = False (away)
    - "Girls vacation" → girls = False (away)
    - "Boys makeup weekend" → boys = True (home)
    
    Args:
        check_date: Date to check
        events: List of exception events
        tz: Timezone
    
    Returns:
        Dict with "boys" and/or "girls" boolean overrides, plus "_dates" list
    """
    day_start = datetime.combine(check_date, datetime.min.time()).replace(tzinfo=tz)
    day_end = datetime.combine(check_date, datetime.max.time()).replace(tzinfo=tz)
    
    exceptions = {"_dates": []}
    
    for event in events:
        from utils.calendar_parser import parse_activity_datetime
        
        start = parse_activity_datetime(event["start"])
        end = parse_activity_datetime(event["end"])
        
        # Check if event overlaps this day
        if start < day_end and end > day_start:
            summary = event.get("summary", "").lower()
            
            # Determine which group
            is_boys = "boys" in summary or "boy" in summary
            is_girls = "girls" in summary or "girl" in summary
            
            # Determine home or away
            # Keywords for away: away, mom, mother, vacation, trip
            # Keywords for home: home, dad, father, makeup, extra
            away_keywords = ["away", "mom", "mother", "vacation", "trip"]
            home_keywords = ["home", "dad", "father", "makeup", "extra"]
            
            is_away = any(kw in summary for kw in away_keywords)
            is_home = any(kw in summary for kw in home_keywords)
            
            if is_boys:
                if is_away:
                    exceptions["boys"] = False
                elif is_home:
                    exceptions["boys"] = True
            
            if is_girls:
                if is_away:
                    exceptions["girls"] = False
                elif is_home:
                    exceptions["girls"] = True
            
            exceptions["_dates"].append(check_date.isoformat())
    
    return exceptions


def _get_meal_guidance(
    boys_home: bool,
    girls_home: bool,
    complexity: str
) -> str:
    """
    Generate meal planning guidance text for a day.
    
    Args:
        boys_home: Whether boys are home
        girls_home: Whether girls are home
        complexity: Complexity classification
    
    Returns:
        Human-readable guidance string
    """
    # Determine who's home
    if not boys_home and not girls_home:
        return "No kids home - skip meal planning or plan for adults only"
    
    who = []
    if boys_home:
        who.append("boys")
    if girls_home:
        who.append("girls")
    
    who_str = " and ".join(who)
    
    # Match complexity to recipe recommendations
    if complexity == "CALM":
        return f"{who_str.capitalize()} home, calm evening - 45-60min recipes, elaborate meals OK"
    elif complexity == "MODERATE":
        return f"{who_str.capitalize()} home, moderate schedule - 30-45min recipes, one-pot meals"
    elif complexity == "BUSY":
        return f"{who_str.capitalize()} home, busy evening - <30min recipes, slow cooker, or prep-ahead"
    else:  # CHAOTIC
        return f"{who_str.capitalize()} home, chaotic schedule - consider takeout or pre-made meals"
```

### 4. Modify: `tools/homeassistant_tools.py`

Update the `get_meal_planning_context_for_period` tool:

```python
@mcp.tool()
async def get_meal_planning_context_for_period(
    start_date: str,
    end_date: str,
    timezone: str = "America/New_York",
    custody_pattern: str = None,
    cycle_start: str = None,
) -> Dict[str, Any]:
    """
    Get unified meal planning context for a date range.
    
    Uses pattern-based custody schedules combined with activity calendars
    to provide per-day meal planning context including:
    - Custody status (boys/girls HOME/AWAY based on pattern)
    - Activity lists (from activity calendars)
    - Complexity classification (CALM, MODERATE, BUSY, CHAOTIC)
    - Meal planning guidance for each day
    
    Custody is determined by:
    1. Pattern-based schedule (e.g., "2-5-5-2" repeating cycle)
    2. Optional exceptions from custody_exceptions calendar
    
    Activity complexity classification:
    - CALM: No activities → 45-60min recipes
    - MODERATE: 1 activity → 30-45min recipes
    - BUSY: 2 activities or 1 late (after 6pm) → <30min recipes, slow cooker
    - CHAOTIC: 3+ activities or 2+ late → takeout recommended
    
    Args:
        start_date: Start date in ISO format (YYYY-MM-DD)
        end_date: End date in ISO format (YYYY-MM-DD) 
        timezone: Timezone string (default: America/New_York)
        custody_pattern: Pattern name (optional, defaults to env CUSTODY_PATTERN):
            - "2-5-5-2" (2 days A, 5 days B, 5 days A, 2 days B)
            - "3-4-4-3" (3 days A, 4 days B, 4 days A, 3 days B)
            - "2-2-3" (2 days A, 2 days B, 3 days A, weekly cycle)
            - "2-2-5-5" (2-2-5-5 pattern)
            - "week-on-week-off" (alternating weeks)
            - "every-other-weekend" (weekdays A, alternating weekends)
        cycle_start: Cycle anchor date in ISO format (optional, defaults to env CUSTODY_CYCLE_START)
    
    Returns:
        Dict with:
            - date_range: {start, end, timezone}
            - pattern_info: {name, description, cycle_days, cycle_start}
            - combined: [...] per-day contexts with custody, activities, complexity
    
    Example response:
        {
          "date_range": {
            "start": "2026-02-06",
            "end": "2026-02-12",
            "timezone": "America/New_York"
          },
          "pattern_info": {
            "name": "2-5-5-2",
            "description": "2 days A, 5 days B, 5 days A, 2 days B",
            "cycle_days": 14,
            "cycle_start": "2026-01-05"
          },
          "combined": [
            {
              "date": "2026-02-06",
              "day_of_week": "Thursday",
              "custody": {
                "boys": "HOME",
                "girls": "AWAY",
                "from_exception": false
              },
              "activities": {
                "benci_boys": [
                  {
                    "summary": "Hockey Practice",
                    "start": "2026-02-06T18:30:00-05:00",
                    "end": "2026-02-06T20:00:00-05:00",
                    "location": "Ice Rink",
                    "description": ""
                  }
                ],
                "boycivengas": [],
                "count": 1
              },
              "complexity": "MODERATE",
              "meal_planning_guidance": "Boys home, moderate schedule - 30-45min recipes, one-pot meals"
            },
            ...
          ]
        }
    """
    try:
        logger.info(
            {
                "event": "get_meal_planning_context",
                "start_date": start_date,
                "end_date": end_date,
                "timezone": timezone,
                "custody_pattern": custody_pattern,
                "cycle_start": cycle_start,
            }
        )

        context = await get_meal_planning_context(
            ha,
            start_date,
            end_date,
            timezone,
            custody_pattern=custody_pattern,
            cycle_start=cycle_start,
        )

        return context

    except Exception as e:
        logger.error(
            {
                "event": "get_meal_planning_context_error",
                "start_date": start_date,
                "end_date": end_date,
                "error": str(e),
            }
        )
        raise ToolError(f"Failed to get meal planning context: {str(e)}")
```

**Remove these tools (no longer needed):**
- `get_custody_schedule()` - replaced by pattern calculation
- Can keep `get_family_events()` for debugging, but not required for main workflow

### 5. Server Configuration

**Environment Variables:**

Add to your deployment configuration (Kubernetes secrets, .env file, etc.):

```bash
# Custody pattern configuration
CUSTODY_PATTERN=2-5-5-2
CUSTODY_CYCLE_START=2026-01-05

# Optional: Different patterns for blended families
# (Requires code modification to support separate boys/girls patterns)
# BOYS_PATTERN=2-5-5-2
# GIRLS_PATTERN=week-on-week-off
```

**Kubernetes ConfigMap/Secret Example:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mealie-mcp-config
data:
  CUSTODY_PATTERN: "2-5-5-2"
  CUSTODY_CYCLE_START: "2026-01-05"
  
---
apiVersion: v1
kind: Secret
metadata:
  name: mealie-mcp-secrets
type: Opaque
stringData:
  mealie-token: "your-mealie-token"
  ha-token: "your-ha-token"
```

**Deployment:**

```yaml
env:
  - name: MEALIE_URL
    value: "https://mealie-mcp-server.taildda370.ts.net"
  - name: MEALIE_TOKEN
    valueFrom:
      secretKeyRef:
        name: mealie-mcp-secrets
        key: mealie-token
  - name: HA_URL
    value: "https://home-assistant.taildda370.ts.net"
  - name: HA_TOKEN
    valueFrom:
      secretKeyRef:
        name: mealie-mcp-secrets
        key: ha-token
  - name: CUSTODY_PATTERN
    valueFrom:
      configMapKeyRef:
        name: mealie-mcp-config
        key: CUSTODY_PATTERN
  - name: CUSTODY_CYCLE_START
    valueFrom:
      configMapKeyRef:
        name: mealie-mcp-config
        key: CUSTODY_CYCLE_START
```

## Home Assistant Calendar Changes

### Optional Exception Calendar

Create a new calendar in Home Assistant for custody exceptions:

**Configuration.yaml:**

```yaml
calendar:
  - platform: local
    name: "Custody Exceptions"
```

**Usage:**

Add events to this calendar when custody deviates from pattern:

- "Boys with mom" (Feb 14-16) - Boys away for makeup weekend
- "Girls vacation with dad" (Feb 20-27) - Girls away for vacation
- "Boys extra night" (Mar 5) - Boys home extra night

The MCP server will automatically detect and apply these exceptions.

### Existing Calendars to Remove

After testing pattern-based approach, you can remove:
- `boys_custody_schedule` calendar events (pattern handles this)
- `girls_custody_schedule` calendar events (pattern handles this)

Keep:
- `benci_boys` activity calendar
- `boycivengas` activity calendar

## Testing & Validation

### 1. Pattern Validation

```python
from utils.custody_patterns import CustodyPattern

# Verify your pattern configuration
schedule = CustodyPattern(
    pattern_name="2-5-5-2",
    cycle_start="2026-01-05"
)

# Visualize
print(schedule.visualize())

# Expected output:
# Pattern: 2 days A, 5 days B, 5 days A, 2 days B
# Cycle: 14 days
# Anchor: 2026-01-05
# 
# | 0| 1| 2| 3| 4| 5| 6| 7| 8| 9|10|11|12|13|
# --------------------------------------------
# Boys  | X| X|  |  |  |  |  | X| X| X| X| X|  |  |
# Girls | X| X|  |  |  |  |  | X| X| X| X| X|  |  |
```

### 2. Date Range Testing

```python
from datetime import date

# Test specific dates against pattern
test_dates = [
    ("2026-01-05", True, True),   # Day 0: Both home
    ("2026-01-06", True, True),   # Day 1: Both home
    ("2026-01-07", False, False), # Day 2: Both away (start of 5-day)
    ("2026-01-12", True, True),   # Day 7: Both home (start of 5-day)
]

for date_str, expected_boys, expected_girls in test_dates:
    check = date.fromisoformat(date_str)
    status = schedule.get_status(check)
    assert status["boys"] == expected_boys, f"{date_str}: Expected boys={expected_boys}"
    assert status["girls"] == expected_girls, f"{date_str}: Expected girls={expected_girls}"
    print(f"✓ {date_str}: boys={status['boys']}, girls={status['girls']}")
```

### 3. Integration Testing

```bash
# Test the MCP tool directly
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_meal_planning_context_for_period",
      "arguments": {
        "start_date": "2026-02-06",
        "end_date": "2026-02-12"
      }
    },
    "id": 1
  }'
```

### 4. Exception Calendar Testing

Add test event to custody_exceptions calendar:
- Summary: "Boys with mom"
- Date: Tomorrow
- Expected: Boys should show AWAY even if pattern says HOME

## Migration Path

### Phase 1: Deploy Pattern-Based Code (No Breaking Changes)

1. Add `custody_patterns.py` file
2. Deploy modified code with backward compatibility
3. Keep existing calendar tools working
4. Test pattern calculation in parallel

### Phase 2: Switch to Pattern-Based Tool

1. Update SKILL.md to use new unified tool
2. Update Claude's configuration to prefer pattern-based tool
3. Test with real meal planning sessions
4. Verify exception handling works

### Phase 3: Cleanup (Optional)

1. Remove old custody calendar tools if desired
2. Archive custody calendar events
3. Simplify Home Assistant calendar configuration

## Benefits Summary

**Code Reduction:**
- Remove ~250 lines from calendar_parser.py
- Remove ~100 lines from meal_planning_context.py
- Add ~150 lines for custody_patterns.py
- **Net reduction: ~200 lines** (~40% less code)

**Complexity Reduction:**
- No datetime parsing edge cases for custody
- No interval merging algorithm
- No FULL_ON/PARTIAL_ON/OFF logic
- Simple array indexing vs complex event processing

**User Experience:**
- Self-documenting pattern: "We're on 2-5-5-2"
- Visual validation of pattern configuration
- Exceptions stand out clearly
- Less calendar maintenance

**LLM Experience:**
- Simpler mental model for Claude
- Clearer natural language responses
- Faster processing (less data to parse)
- Better confidence in custody interpretation

## Future Enhancements

1. **Web UI for pattern configuration**: Visual editor for custody patterns
2. **Pattern templates**: Save custom blended family patterns
3. **Pattern validation**: Ensure patterns match co-parent's understanding
4. **Transition notifications**: Alert when pattern switches to next phase
5. **Non-MCP alternative**: Explore Home Assistant binary sensors or browser-based artifacts