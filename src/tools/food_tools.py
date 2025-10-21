import logging
import traceback
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from mealie import MealieFetcher

logger = logging.getLogger("mealie-mcp")


def register_food_tools(mcp: FastMCP, mealie: MealieFetcher) -> None:
    """Register all food-related tools with the MCP server."""

    @mcp.tool()
    async def get_foods(
        search: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get all ingredient foods with pagination and filtering.

        Args:
            search: Search term to filter foods by name
            page: Page number for pagination
            per_page: Number of items per page

        Returns:
            Dict[str, Any]: Food items with details like ID, name, description, and households
        """
        try:
            logger.info(
                {
                    "message": "Fetching foods",
                    "search": search,
                    "page": page,
                    "per_page": per_page,
                }
            )
            return await mealie.get_foods(
                search=search,
                page=page,
                per_page=per_page,
            )
        except Exception as e:
            error_msg = f"Error fetching foods: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug(
                {"message": "Error traceback", "traceback": traceback.format_exc()}
            )
            raise ToolError(error_msg)

    @mcp.tool()
    async def get_foods_on_hand(
        search: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get ingredient foods that are currently on hand (in your pantry).

        This returns only foods where householdsWithIngredientFood is not empty,
        indicating the food is currently available in someone's pantry/household.

        Args:
            search: Search term to filter on-hand foods by name
            page: Page number for pagination
            per_page: Number of items per page

        Returns:
            Dict[str, Any]: On-hand food items with household information
        """
        try:
            logger.info(
                {
                    "message": "Fetching foods on hand",
                    "search": search,
                    "page": page,
                    "per_page": per_page,
                }
            )
            return await mealie.get_foods_on_hand(
                search=search,
                page=page,
                per_page=per_page,
            )
        except Exception as e:
            error_msg = f"Error fetching foods on hand: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug(
                {"message": "Error traceback", "traceback": traceback.format_exc()}
            )
            raise ToolError(error_msg)

    @mcp.tool()
    async def get_food_by_id(food_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific food by its ID.

        Args:
            food_id: UUID of the food to retrieve

        Returns:
            Dict[str, Any]: Detailed food information including aliases, labels, and households
        """
        try:
            logger.info({"message": "Fetching food by ID", "food_id": food_id})
            return await mealie.get_food_by_id(food_id)
        except Exception as e:
            error_msg = f"Error fetching food with ID '{food_id}': {str(e)}"
            logger.error({"message": error_msg, "food_id": food_id})
            logger.debug(
                {"message": "Error traceback", "traceback": traceback.format_exc()}
            )
            raise ToolError(error_msg)

    def _parse_description(description: str) -> Dict[str, str]:
        """Parse pipe-separated description fields.
        
        Format: "Quantity: 2 lbs | Units: 2 | Price: $4.99ea"
        
        Args:
            description: Description string with pipe-separated fields
            
        Returns:
            Dict mapping field names to values
        """
        result = {}
        if not description:
            return result
            
        for field in description.split(" | "):
            if ": " in field:
                key, value = field.split(": ", 1)
                result[key.strip()] = value.strip()
        return result

    def _build_description(
        existing_desc: str,
        quantity: Optional[str] = None,
        units: Optional[str] = None,
        price: Optional[str] = None,
    ) -> str:
        """Build pipe-separated description from fields.
        
        Args:
            existing_desc: Existing description to preserve non-updated fields
            quantity: Quantity value (e.g., "2 lbs")
            units: Units value (e.g., "2")
            price: Price value (e.g., "$4.99ea")
            
        Returns:
            Updated description string
        """
        # Parse existing fields
        fields = _parse_description(existing_desc)
        
        # Update with new values
        if quantity is not None:
            fields["Quantity"] = quantity
        if units is not None:
            fields["Units"] = units
        if price is not None:
            fields["Price"] = price
            
        # Build new description
        if not fields:
            return ""
        return " | ".join([f"{k}: {v}" for k, v in fields.items()])

    @mcp.tool()
    async def update_food_quantity(
        food_id: str,
        quantity: Optional[str] = None,
        units: Optional[str] = None,
        price: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update quantity information for a food item using pipe-separated description format.
        
        Updates the food's description field with quantity/units/price information in the format:
        "Quantity: 2 lbs | Units: 2 | Price: $4.99ea"
        
        Only updates the fields you provide, preserving existing values for other fields.
        
        Args:
            food_id: UUID of the food to update
            quantity: Quantity with unit (e.g., "2 lbs", "3 cups")
            units: Number of units (e.g., "2", "5")
            price: Price per unit (e.g., "$4.99ea", "$2.50/lb")
            
        Returns:
            Dict[str, Any]: Updated food information
        """
        try:
            logger.info({
                "message": "Updating food quantity",
                "food_id": food_id,
                "quantity": quantity,
                "units": units,
                "price": price,
            })
            
            # Get current food to preserve existing data
            current_food = await mealie.get_food_by_id(food_id)
            existing_desc = current_food.get("description", "")
            
            # Build new description
            new_desc = _build_description(existing_desc, quantity, units, price)
            
            # Update food
            update_data = {"description": new_desc}
            result = await mealie.update_food(food_id, update_data)
            
            logger.info({
                "message": "Successfully updated food quantity",
                "food_id": food_id,
                "new_description": new_desc,
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Error updating food quantity for '{food_id}': {str(e)}"
            logger.error({"message": error_msg, "food_id": food_id})
            logger.debug(
                {"message": "Error traceback", "traceback": traceback.format_exc()}
            )
            raise ToolError(error_msg)

    @mcp.tool()
    async def add_food_to_inventory(
        name: str,
        household_id: str,
        quantity: Optional[str] = None,
        units: Optional[str] = None,
        price: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a new food to inventory and associate it with a household.
        
        Creates a new food item with quantity information and adds it to the specified
        household's inventory.
        
        Args:
            name: Name of the food item
            household_id: UUID of the household to add the food to
            quantity: Quantity with unit (e.g., "2 lbs", "3 cups")
            units: Number of units (e.g., "2", "5")
            price: Price per unit (e.g., "$4.99ea", "$2.50/lb")
            
        Returns:
            Dict[str, Any]: Created food information
        """
        try:
            logger.info({
                "message": "Adding food to inventory",
                "name": name,
                "household_id": household_id,
            })
            
            # Build description from quantity info
            description = _build_description("", quantity, units, price)
            
            # Create food data
            food_data = {
                "name": name,
                "description": description,
                "householdsWithIngredientFood": [household_id],
            }
            
            result = await mealie.create_food(food_data)
            
            logger.info({
                "message": "Successfully added food to inventory",
                "food_id": result.get("id"),
                "name": name,
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Error adding food '{name}' to inventory: {str(e)}"
            logger.error({"message": error_msg, "name": name})
            logger.debug(
                {"message": "Error traceback", "traceback": traceback.format_exc()}
            )
            raise ToolError(error_msg)

    @mcp.tool()
    async def remove_food_from_inventory(food_id: str) -> Dict[str, Any]:
        """Remove a food item from inventory.
        
        Deletes the food item completely from the system.
        
        Args:
            food_id: UUID of the food to remove
            
        Returns:
            Dict[str, Any]: Deletion confirmation
        """
        try:
            logger.info({
                "message": "Removing food from inventory",
                "food_id": food_id,
            })
            
            result = await mealie.delete_food(food_id)
            
            logger.info({
                "message": "Successfully removed food from inventory",
                "food_id": food_id,
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Error removing food '{food_id}' from inventory: {str(e)}"
            logger.error({"message": error_msg, "food_id": food_id})
            logger.debug(
                {"message": "Error traceback", "traceback": traceback.format_exc()}
            )
            raise ToolError(error_msg)
