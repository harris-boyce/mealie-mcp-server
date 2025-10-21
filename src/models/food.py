from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class IngredientFoodAlias(BaseModel):
    """Alias for an ingredient food."""

    id: Optional[str] = None
    name: str


class IngredientFood(BaseModel):
    """Represents an ingredient food in Mealie."""

    id: str
    name: str
    pluralName: Optional[str] = None
    description: str = ""
    extras: Optional[Dict[str, Any]] = {}
    labelId: Optional[str] = None
    aliases: List[IngredientFoodAlias] = []
    householdsWithIngredientFood: List[str] = []
    label: Optional[Dict[str, Any]] = None
    createdAt: Optional[str] = None
    updateAt: Optional[str] = None


class IngredientFoodPagination(BaseModel):
    """Pagination response for ingredient foods."""

    page: int
    per_page: int
    total: int
    total_pages: int
    items: List[IngredientFood]
    next: Optional[str] = None
    previous: Optional[str] = None
