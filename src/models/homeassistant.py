from typing import List, Optional, Any

from pydantic import BaseModel, validator


class CalendarEvent(BaseModel):
    """Represents a calendar event from Home Assistant.

    Home Assistant returns `start`/`end` as either a string or a dict with
    `date` (all-day) or `dateTime` (timestamp). Accept both formats and
    normalize to a string.
    """

    start: str  # ISO 8601 datetime string or date string
    end: str  # ISO 8601 datetime string or date string
    summary: str
    description: Optional[str] = None
    location: Optional[str] = None

    @validator("start", "end", pre=True)
    def _parse_start_end(cls, v: Any) -> str:
        if isinstance(v, dict):
            # Prefer dateTime (timestamp) if present, otherwise date (all-day)
            if "dateTime" in v and isinstance(v["dateTime"], str):
                return v["dateTime"]
            if "date" in v and isinstance(v["date"], str):
                return v["date"]
            # Fallback: try common keys
            for key in ("start", "end"):
                if key in v and isinstance(v[key], str):
                    return v[key]
            # Last resort: stringify the dict
            return str(v)
        return v


class Calendar(BaseModel):
    """Represents a calendar entity in Home Assistant."""

    entity_id: str
    name: str


class CalendarEventsResponse(BaseModel):
    """Response containing calendar events for a specific calendar."""

    calendar: str
    start: str
    end: str
    events: List[CalendarEvent]
