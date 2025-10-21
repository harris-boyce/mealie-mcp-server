"""Meal planning context with pattern-based custody schedules.

This module orchestrates pattern-based custody schedules with activity calendars
to provide unified meal planning context.
"""

import os
from datetime import date, timedelta
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from utils.custody_patterns import CustodyPattern
from utils.calendar_parser import (
    get_activities_for_day,
    classify_day_complexity,
)


async def get_meal_planning_context(
    client,  # HomeAssistantClient instance
    start_date: str,
    end_date: str,
    tz: str = "America/New_York",
    custody_pattern: Optional[str] = None,
    cycle_start: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get unified meal planning context using pattern-based custody schedules.

    Combines pattern-based custody configuration with activity calendars
    to produce per-day context for meal planning.

    Custody is determined by:
    1. Pattern-based schedule (e.g., "2-2-3-2-2-3-blended" repeating cycle)
    2. Configured anchor date (cycle start)
    3. Separate patterns for boys and girls (supports blended families)

    Activity complexity is still calendar-based:
    - Fetches benci_boys and boycivengas activity calendars
    - Classifies day as CALM, MODERATE, BUSY, or CHAOTIC
    - Based on activity count and late activities (after 6pm)

    Args:
        client: HomeAssistantClient with calendar methods
        start_date: ISO date string (YYYY-MM-DD)
        end_date: ISO date string (YYYY-MM-DD)
        tz: Timezone string (default: America/New_York)
        custody_pattern: Pattern name (overrides CUSTODY_PATTERN env var)
        cycle_start: Cycle anchor date (overrides CUSTODY_CYCLE_START env var)

    Returns:
        Dict with:
            - date_range: {start, end, timezone}
            - pattern_info: {name, description, cycle_days, cycle_start}
            - combined: [...] per-day contexts with custody, activities, complexity

    Example response:
        {
          "date_range": {
            "start": "2026-01-26",
            "end": "2026-02-08",
            "timezone": "America/New_York"
          },
          "pattern_info": {
            "name": "2-2-3-2-2-3-blended",
            "description": "Custom blended: 2-2-3 alternating...",
            "cycle_days": 14,
            "cycle_start": "2026-01-26"
          },
          "combined": [
            {
              "date": "2026-01-26",
              "day_of_week": "Sunday",
              "custody": {
                "boys": "AWAY",
                "girls": "HOME"
              },
              "activities": {
                "benci_boys": [],
                "boycivengas": [],
                "count": 0
              },
              "complexity": "CALM",
              "meal_planning_guidance": "Girls home, calm evening - 45-60min recipes..."
            },
            ...
          ]
        }
    """
    timezone = ZoneInfo(tz)
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    # Initialize custody patterns from config or parameters
    pattern_name = custody_pattern or os.getenv("CUSTODY_PATTERN", "2-2-3-2-2-3-blended")
    anchor_date = cycle_start or os.getenv("CUSTODY_CYCLE_START", "2026-01-26")

    # Create separate pattern instances for boys and girls
    boys_pattern = CustodyPattern(
        pattern_name=pattern_name,
        cycle_start=anchor_date,
        group="boys"
    )
    girls_pattern = CustodyPattern(
        pattern_name=pattern_name,
        cycle_start=anchor_date,
        group="girls"
    )

    # Calculate days ahead from now
    days_ahead = (end - date.today()).days

    # Fetch activity calendars only (custody is now pattern-based!)
    benci_boys_response = await client.get_calendar_events_by_name(
        "benci_boys",
        days_ahead=days_ahead
    )
    boycivengas_response = await client.get_calendar_events_by_name(
        "boycivengas",
        days_ahead=days_ahead
    )

    # Convert to dicts for processing
    benci_boys_events = [event.model_dump() for event in benci_boys_response]
    boycivengas_events = [event.model_dump() for event in boycivengas_response]

    # Build per-day context
    combined_days = []
    current = start

    while current <= end:
        # Get custody status from patterns (simple boolean check!)
        boys_home = boys_pattern.is_present(current)
        girls_home = girls_pattern.is_present(current)

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
            "description": boys_pattern.pattern_config.get("description", "Custom"),
            "cycle_days": boys_pattern.cycle_days,
            "cycle_start": anchor_date,
        },
        "combined": combined_days,
    }


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
        complexity: Complexity classification (CALM, MODERATE, BUSY, CHAOTIC)

    Returns:
        Human-readable guidance string

    Examples:
        >>> _get_meal_guidance(True, True, "CALM")
        'Boys and girls home, calm evening - 45-60min recipes, elaborate meals OK'
        >>> _get_meal_guidance(False, False, "CALM")
        'No kids home - skip meal planning or plan for adults only'
        >>> _get_meal_guidance(True, False, "BUSY")
        'Boys home, busy evening - <30min recipes, slow cooker, or prep-ahead'
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
