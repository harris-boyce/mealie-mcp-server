"""Simplified calendar event parsing for activity calendars only.

This module handles parsing of activity calendar events for meal planning context.
Custody schedules are now handled by pattern-based configuration (see custody_patterns.py).
"""

from datetime import datetime, date
from typing import Any, Dict, List
from zoneinfo import ZoneInfo


def parse_activity_datetime(dt_value: Any, default_tz: str = "America/New_York") -> datetime:
    """
    Parse Home Assistant calendar event datetime for activities.

    Simplified version that handles common datetime formats from Home Assistant.

    Accepts either:
    - ISO string: "2026-02-11T12:00:00-05:00"
    - Date string: "2026-02-11"
    - Dict with 'dateTime': {"dateTime": "2026-02-11T12:00:00-05:00"}
    - Dict with 'date': {"date": "2026-02-11"}

    Args:
        dt_value: Datetime value in various formats
        default_tz: Default timezone if not specified in value

    Returns:
        Timezone-aware datetime

    Raises:
        ValueError: If datetime value cannot be parsed

    Examples:
        >>> parse_activity_datetime("2026-02-11T12:00:00-05:00")
        datetime.datetime(2026, 2, 11, 12, 0, tzinfo=...)
        >>> parse_activity_datetime("2026-02-11", "America/New_York")
        datetime.datetime(2026, 2, 11, 0, 0, tzinfo=ZoneInfo('America/New_York'))
    """
    if isinstance(dt_value, str):
        # Try parsing as datetime first
        if "T" in dt_value:
            return datetime.fromisoformat(dt_value)
        # Parse as date, set to start of day
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

    raise ValueError(f"Cannot parse datetime value: {dt_value}")


def get_activities_for_day(
    day: date,
    events: List[Dict[str, Any]],
    tz: ZoneInfo
) -> List[Dict[str, Any]]:
    """
    Get all activity events that occur on a specific day.

    Args:
        day: Date to check
        events: List of activity events from calendar
        tz: Timezone for day boundaries

    Returns:
        List of activities for this day with normalized datetime strings

    Examples:
        >>> from zoneinfo import ZoneInfo
        >>> from datetime import date
        >>> events = [
        ...     {
        ...         "start": "2026-02-11T18:00:00-05:00",
        ...         "end": "2026-02-11T19:30:00-05:00",
        ...         "summary": "Hockey Practice"
        ...     }
        ... ]
        >>> tz = ZoneInfo("America/New_York")
        >>> activities = get_activities_for_day(date(2026, 2, 11), events, tz)
        >>> len(activities)
        1
        >>> activities[0]["summary"]
        'Hockey Practice'
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

    Classification rules:
    - 3+ activities OR 2+ late activities (after 6pm) → CHAOTIC
    - 2 activities OR 1 late activity → BUSY
    - 1 activity → MODERATE
    - 0 activities → CALM

    Args:
        activities: List of activity events for the day
        tz: Timezone for time-based checks

    Returns:
        Complexity label: CALM, MODERATE, BUSY, or CHAOTIC

    Examples:
        >>> from zoneinfo import ZoneInfo
        >>> tz = ZoneInfo("America/New_York")
        >>> # No activities
        >>> classify_day_complexity([], tz)
        'CALM'
        >>> # One activity
        >>> classify_day_complexity([{"start": "2026-02-11T15:00:00-05:00"}], tz)
        'MODERATE'
        >>> # One late activity (6pm+)
        >>> classify_day_complexity([{"start": "2026-02-11T19:00:00-05:00"}], tz)
        'BUSY'
    """
    if not activities:
        return "CALM"

    # Count activities
    count = len(activities)

    # Check for late activities (after 6pm)
    late_activities = []
    for activity in activities:
        start = parse_activity_datetime(activity["start"])
        if start.hour >= 18:  # 6pm or later
            late_activities.append(activity)

    # Classification rules
    if count >= 3 or len(late_activities) >= 2:
        return "CHAOTIC"
    elif count == 2 or len(late_activities) == 1:
        return "BUSY"
    elif count == 1:
        return "MODERATE"
    else:
        return "CALM"
