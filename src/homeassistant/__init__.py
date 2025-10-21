from homeassistant.calendar import CalendarMixin
from homeassistant.client import HomeAssistantClient, HomeAssistantError


class HomeAssistantFetcher(CalendarMixin, HomeAssistantClient):
    """Unified Home Assistant API client with all mixins."""

    pass


__all__ = ["HomeAssistantFetcher", "HomeAssistantError"]
