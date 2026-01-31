"""
MedMarket Bot - Модуль сервисов.

Этот пакет содержит бизнес-логику приложения, разделённую
на отдельные сервисы по функциональности.

Доступные сервисы:
    - RecipeService: Поиск и фильтрация рецептов по диагнозам.
    - GPTService: AI-диетолог на базе OpenAI GPT-4.
    - ShopService: Поиск магазинов и сравнение цен.

Example:
    Использование сервисов::

        from services import RecipeService, GPTService, ShopService

        recipe_service = RecipeService()
        recipes = recipe_service.search_recipes("курица", has_gout=True)

        gpt_service = GPTService()
        answer = gpt_service.ask_dietician("Что можно есть при подагре?")

        shop_service = ShopService()
        shops = shop_service.find_nearby_shops(55.7558, 37.6173)

Author: MedMarket Team
License: MIT
Version: 1.0.0
"""

from services.recipe_service import RecipeService
from services.gpt_service import GPTService
from services.shop_service import ShopService

__all__ = [
    "RecipeService",
    "GPTService",
    "ShopService",
]
