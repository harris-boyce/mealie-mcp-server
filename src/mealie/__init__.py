from .client import MealieClient
from .food import FoodMixin
from .group import GroupMixin
from .mealplan import MealplanMixin
from .recipe import RecipeMixin
from .user import UserMixin


class MealieFetcher(
    RecipeMixin,
    FoodMixin,
    UserMixin,
    GroupMixin,
    MealplanMixin,
    MealieClient,
):
    pass
