from typing import Optional

from .food_tools import register_food_tools
from .mealplan_tools import register_mealplan_tools
from .recipe_tools import register_recipe_tools
from .homeassistant_tools import register_homeassistant_tools


def register_all_tools(mcp, mealie, ha=None):
    """Register all tools with the MCP server.
    
    Args:
        mcp: FastMCP server instance
        mealie: MealieFetcher instance
        ha: Optional HomeAssistantFetcher instance
    """
    register_recipe_tools(mcp, mealie)
    register_mealplan_tools(mcp, mealie)
    register_food_tools(mcp, mealie)
    
    # Register Home Assistant tools if fetcher provided
    if ha is not None:
        register_homeassistant_tools(mcp, ha)


__all__ = [
    "register_all_tools",
    "register_recipe_tools",
    "register_mealplan_tools",
    "register_food_tools",
    "register_homeassistant_tools",
]
