import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from models.homeassistant import CalendarEventsResponse
from homeassistant import HomeAssistantFetcher
from tools.meal_planning_context import get_meal_planning_context

logger = logging.getLogger(__name__)


def register_homeassistant_tools(mcp: FastMCP, ha: HomeAssistantFetcher) -> None:
    """Register Home Assistant tools with the MCP server."""

    @mcp.tool()
    async def get_family_events(
        calendar: str,
        days_ahead: int = 7,
    ) -> Dict[str, Any]:
        """
        Get family activity events from Home Assistant calendar.

        Fetches activity/event calendars that impact meal planning complexity.
        These calendars track scheduled activities (practices, games, etc.)
        that affect available time for meal preparation.

        Args:
            calendar: Calendar name without 'calendar.' prefix
                     ("benci_boys" or "boycivengas")
            days_ahead: Number of days to look ahead (default 7)

        Returns:
            Dict with calendar name, date range, and list of calendar events

        Note:
            Custody schedules are now pattern-based (see CUSTODY_PATTERN
            environment variable). This tool is for activity calendars only.
        """
        try:
            logger.info(
                {
                    "event": "get_family_events",
                    "calendar": calendar,
                    "days_ahead": days_ahead,
                }
            )

            start = datetime.now().isoformat()
            end = (datetime.now() + timedelta(days=days_ahead)).isoformat()

            events = await ha.get_calendar_events_by_name(calendar, days_ahead)

            response = CalendarEventsResponse(
                calendar=calendar,
                start=start,
                end=end,
                events=events,
            )

            return response.model_dump()

        except Exception as e:
            logger.error(
                {
                    "event": "get_family_events_error",
                    "calendar": calendar,
                    "error": str(e),
                }
            )
            raise ToolError(f"Failed to get family events: {str(e)}")

    @mcp.tool()
    async def get_all_calendars() -> Dict[str, Any]:
        """
        List all available calendars in Home Assistant.

        Returns:
            Dict containing list of calendar entities with names and entity_ids
        """
        try:
            logger.info({"event": "get_all_calendars"})

            calendars = await ha.list_calendars()

            return {
                "calendars": [cal.model_dump() for cal in calendars],
                "count": len(calendars),
            }

        except Exception as e:
            logger.error(
                {
                    "event": "get_all_calendars_error",
                    "error": str(e),
                }
            )
            raise ToolError(f"Failed to get calendars: {str(e)}")

    @mcp.tool()
    async def get_meal_planning_context_for_period(
        start_date: str,
        end_date: str,
        timezone: str = "America/New_York",
        custody_pattern: Optional[str] = None,
        cycle_start: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get unified meal planning context for a date range.

        Uses PATTERN-BASED custody schedules combined with activity calendars
        to provide per-day meal planning context including:
        - Custody status (boys/girls HOME/AWAY based on pattern)
        - Activity lists (from activity calendars)
        - Complexity classification (CALM, MODERATE, BUSY, CHAOTIC)
        - Meal planning guidance for each day

        Custody is determined by:
        1. Pattern-based schedule (e.g., "2-2-3-2-2-3-blended" repeating cycle)
        2. Configured anchor date (cycle start)
        3. Separate patterns for boys and girls (supports blended families)

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
                - "2-2-3-2-2-3-blended" (custom blended family pattern)
            cycle_start: Cycle anchor date in ISO format (optional, defaults to env CUSTODY_CYCLE_START)

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
                "description": "Custom blended: 2-2-3 alternating, 3-day weekend together, 3-day parent break",
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
                  "meal_planning_guidance": "Girls home, calm evening - 45-60min recipes, elaborate meals OK"
                },
                {
                  "date": "2026-01-30",
                  "day_of_week": "Thursday",
                  "custody": {
                    "boys": "HOME",
                    "girls": "HOME"
                  },
                  "activities": {
                    "benci_boys": [
                      {
                        "summary": "Hockey Practice",
                        "start": "2026-01-30T18:30:00-05:00",
                        "end": "2026-01-30T20:00:00-05:00",
                        "location": "Ice Rink",
                        "description": ""
                      }
                    ],
                    "boycivengas": [],
                    "count": 1
                  },
                  "complexity": "MODERATE",
                  "meal_planning_guidance": "Boys and girls home, moderate schedule - 30-45min recipes, one-pot meals"
                },
                {
                  "date": "2026-02-06",
                  "day_of_week": "Thursday",
                  "custody": {
                    "boys": "AWAY",
                    "girls": "AWAY"
                  },
                  "activities": {
                    "benci_boys": [],
                    "boycivengas": [],
                    "count": 0
                  },
                  "complexity": "CALM",
                  "meal_planning_guidance": "No kids home - skip meal planning or plan for adults only"
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
