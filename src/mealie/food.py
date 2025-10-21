import logging
from typing import Any, Dict, List, Optional

from utils import format_api_params

logger = logging.getLogger("mealie-mcp")


class FoodMixin:
    """Mixin class for food-related API endpoints"""

    async def get_foods(
        self,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
        order_by_null_position: Optional[str] = None,
        order_direction: Optional[str] = "desc",
        query_filter: Optional[str] = None,
        pagination_seed: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get all foods with pagination and filtering.

        Args:
            search: Search term to filter foods by name
            order_by: Field to order results by
            order_by_null_position: How to handle nulls in ordering ('first' or 'last')
            order_direction: Direction to order results ('asc' or 'desc')
            query_filter: Advanced query filter
            pagination_seed: Seed for consistent pagination
            page: Page number to retrieve
            per_page: Number of items per page

        Returns:
            JSON response containing food items and pagination information
        """

        param_dict = {
            "search": search,
            "orderBy": order_by,
            "orderByNullPosition": order_by_null_position,
            "orderDirection": order_direction,
            "queryFilter": query_filter,
            "paginationSeed": pagination_seed,
            "page": page,
            "perPage": per_page,
        }

        params = format_api_params(param_dict)

        logger.debug({"message": "Getting foods", "params": params})
        response = await self._handle_request("GET", "/api/foods", params=params)
        logger.info(
            {
                "message": "Successfully retrieved foods",
                "count": len(response.get("items", [])),
                "page": response.get("page"),
                "total": response.get("total"),
            }
        )
        return response

    async def get_foods_on_hand(
        self,
        search: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get foods that are currently on hand (have associated households).

        This filters foods to only return those where householdsWithIngredientFood
        is not empty, indicating the food is currently in someone's pantry.

        Args:
            search: Search term to filter foods by name
            page: Page number to retrieve
            per_page: Number of items per page

        Returns:
            JSON response containing on-hand food items
        """

        logger.debug({"message": "Getting foods on hand", "search": search})

        # Get all foods with the given parameters
        response = await self.get_foods(
            search=search,
            page=page,
            per_page=per_page,
        )

        # Filter to only include foods that are on hand
        if "items" in response:
            on_hand_foods = [
                food
                for food in response["items"]
                if food.get("householdsWithIngredientFood")
                and len(food.get("householdsWithIngredientFood", [])) > 0
            ]

            logger.info(
                {
                    "message": "Filtered foods to on-hand only",
                    "total_foods": len(response.get("items", [])),
                    "on_hand_foods": len(on_hand_foods),
                }
            )

            response["items"] = on_hand_foods
            response["total"] = len(on_hand_foods)

        return response

    async def get_food_by_id(self, food_id: str) -> Dict[str, Any]:
        """Get a specific food by its ID.

        Args:
            food_id: UUID of the food to retrieve

        Returns:
            JSON response containing food details
        """

        logger.debug({"message": "Getting food by ID", "food_id": food_id})
        response = await self._handle_request("GET", f"/api/foods/{food_id}")
        logger.info({"message": "Successfully retrieved food", "food_id": food_id})
        return response

    async def update_food(
        self, food_id: str, food_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a food item.

        Args:
            food_id: UUID of the food to update
            food_data: Dictionary containing food properties to update

        Returns:
            JSON response containing updated food details
        """
        logger.debug({"message": "Updating food", "food_id": food_id})
        response = await self._handle_request(
            "PUT", f"/api/foods/{food_id}", json=food_data
        )
        logger.info({"message": "Successfully updated food", "food_id": food_id})
        return response

    async def create_food(self, food_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new food item.

        Args:
            food_data: Dictionary containing food properties

        Returns:
            JSON response containing created food details
        """
        logger.debug({"message": "Creating food", "name": food_data.get("name")})
        response = await self._handle_request("POST", "/api/foods", json=food_data)
        logger.info(
            {
                "message": "Successfully created food",
                "food_id": response.get("id"),
                "name": response.get("name"),
            }
        )
        return response

    async def delete_food(self, food_id: str) -> Dict[str, Any]:
        """Delete a food item.

        Args:
            food_id: UUID of the food to delete

        Returns:
            JSON response confirming deletion
        """
        logger.debug({"message": "Deleting food", "food_id": food_id})
        response = await self._handle_request("DELETE", f"/api/foods/{food_id}")
        logger.info({"message": "Successfully deleted food", "food_id": food_id})
        return response
