from datetime import datetime, timedelta
from typing import Any, Dict, List

from models.homeassistant import Calendar, CalendarEvent


class CalendarMixin:
    """Mixin for Home Assistant calendar operations."""

    async def get_calendar_events(
        self, entity_id: str, start: str, end: str
    ) -> List[CalendarEvent]:
        """
        Get calendar events for a specific calendar entity.

        Args:
            entity_id: The calendar entity ID (e.g., "calendar.boys_custody_schedule")
            start: Start datetime in ISO 8601 format
            end: End datetime in ISO 8601 format

        Returns:
            List of CalendarEvent objects
        """
        url = f"/api/calendars/{entity_id}"
        params = {"start": start, "end": end}
        response = await self._handle_request("GET", url, params=params)

        # Response is a list of event dictionaries
        events = [CalendarEvent(**event) for event in response]
        return events

    async def list_calendars(self) -> List[Calendar]:
        """
        List all available calendars in Home Assistant.

        Returns:
            List of Calendar objects
        """
        url = "/api/calendars"
        response = await self._handle_request("GET", url)

        # Response is a list of calendar dictionaries
        calendars = [Calendar(**cal) for cal in response]
        return calendars

    async def get_calendar_events_by_name(
        self, calendar_name: str, days_ahead: int = 7
    ) -> List[CalendarEvent]:
        """
        Get calendar events by calendar name with relative date range.

        Args:
            calendar_name: Calendar name without 'calendar.' prefix
            days_ahead: Number of days to look ahead from now

        Returns:
            List of CalendarEvent objects
        """
        entity_id = (
            calendar_name
            if calendar_name.startswith("calendar.")
            else f"calendar.{calendar_name}"
        )

        start = datetime.now().isoformat()
        end = (datetime.now() + timedelta(days=days_ahead)).isoformat()

        return await self.get_calendar_events(entity_id, start, end)
