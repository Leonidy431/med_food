"""
MedMarket Bot - Сервис рецептов.

Этот модуль содержит сервис для поиска и фильтрации рецептов
по диагнозам пользователя. Включает базу рецептов средиземноморской
диеты, оптимизированную для подагры и диабета.

Модуль соответствует стандартам PEP8 и PEP257.

Example:
    Использование сервиса::

        from services.recipe_service import RecipeService

        service = RecipeService()
        recipes = service.search_recipes(
            "курица",
            has_gout=True,
            has_diabetes=True
        )
        for recipe in recipes:
            print(recipe["name"])

Author: MedMarket Team
License: MIT
Version: 1.0.0
"""

import json
import random
from typing import Any, Dict, List, Optional

from loguru import logger

from config import settings


# =============================================================================
# БАЗА РЕЦЕПТОВ СРЕДИЗЕМНОМОРСКОЙ ДИЕТЫ
# =============================================================================

# Рецепты с полной информацией о пищевой ценности и диетических параметрах
RECIPES_DATABASE: List[Dict[str, Any]] = [
    {
        "id": "r_001",
        "name": "Курица с брокколи на пару",
        "description": "Лёгкое диетическое блюдо, идеальное для диабетиков. "
                       "Низкий гликемический индекс и умеренное содержание белка.",
        "calories": 320,
        "proteins": 42,
        "fats": 9,
        "carbs": 18,
        "glycemic_index": 35,
        "purines": 120,  # Умеренно для подагры
        "cooking_time_min": 25,
        "servings": 2,
        "suitable_for_diabetes": True,
        "suitable_for_gout": False,  # Курица содержит пурины
        "suitable_for_celiac": True,
        "category": "main",
        "ingredients": [
            {"name": "Куриное филе", "amount": 300, "unit": "г"},
            {"name": "Брокколи", "amount": 200, "unit": "г"},
            {"name": "Оливковое масло", "amount": 10, "unit": "мл"},
            {"name": "Лимонный сок", "amount": 15, "unit": "мл"},
            {"name": "Соль, перец", "amount": 1, "unit": "по вкусу"},
        ],
        "instructions": [
            "Нарезать куриное филе на небольшие кусочки.",
            "Разделить брокколи на соцветия, промыть.",
            "Выложить курицу и брокколи в пароварку.",
            "Готовить на пару 20-25 минут до готовности.",
            "Полить оливковым маслом и лимонным соком.",
            "Посолить и поперчить по вкусу."
        ]
    },
    {
        "id": "r_002",
        "name": "Салат Средиземноморский",
        "description": "Классический овощной салат, богатый антиоксидантами. "
                       "Подходит для всех диагнозов.",
        "calories": 180,
        "proteins": 5,
        "fats": 12,
        "carbs": 15,
        "glycemic_index": 20,
        "purines": 15,  # Очень низкое содержание
        "cooking_time_min": 15,
        "servings": 2,
        "suitable_for_diabetes": True,
        "suitable_for_gout": True,
        "suitable_for_celiac": True,
        "category": "salad",
        "ingredients": [
            {"name": "Помидоры черри", "amount": 150, "unit": "г"},
            {"name": "Огурец", "amount": 1, "unit": "шт"},
            {"name": "Болгарский перец", "amount": 1, "unit": "шт"},
            {"name": "Красный лук", "amount": 50, "unit": "г"},
            {"name": "Маслины", "amount": 50, "unit": "г"},
            {"name": "Оливковое масло Extra Virgin", "amount": 30, "unit": "мл"},
            {"name": "Лимонный сок", "amount": 15, "unit": "мл"},
            {"name": "Орегано сушёный", "amount": 1, "unit": "ч.л."},
        ],
        "instructions": [
            "Нарезать помидоры пополам.",
            "Огурец нарезать полукольцами.",
            "Перец нарезать кубиками.",
            "Лук нарезать тонкими полукольцами.",
            "Смешать все овощи в салатнике.",
            "Добавить маслины.",
            "Заправить оливковым маслом и лимонным соком.",
            "Посыпать орегано, посолить по вкусу."
        ]
    },
    {
        "id": "r_003",
        "name": "Гречневая каша с овощами",
        "description": "Питательное блюдо с низким ГИ, богатое клетчаткой. "
                       "Идеально для завтрака или гарнира.",
        "calories": 250,
        "proteins": 9,
        "fats": 6,
        "carbs": 42,
        "glycemic_index": 40,
        "purines": 25,
        "cooking_time_min": 30,
        "servings": 2,
        "suitable_for_diabetes": True,
        "suitable_for_gout": True,
        "suitable_for_celiac": True,
        "category": "main",
        "ingredients": [
            {"name": "Гречневая крупа", "amount": 150, "unit": "г"},
            {"name": "Морковь", "amount": 1, "unit": "шт"},
            {"name": "Лук репчатый", "amount": 1, "unit": "шт"},
            {"name": "Кабачок", "amount": 150, "unit": "г"},
            {"name": "Оливковое масло", "amount": 15, "unit": "мл"},
            {"name": "Вода", "amount": 300, "unit": "мл"},
        ],
        "instructions": [
            "Промыть гречку под холодной водой.",
            "Нарезать овощи мелкими кубиками.",
            "Обжарить лук и морковь на оливковом масле 5 минут.",
            "Добавить кабачок, тушить ещё 3 минуты.",
            "Добавить гречку и воду.",
            "Довести до кипения, уменьшить огонь.",
            "Варить 20 минут до готовности гречки.",
            "Посолить по вкусу."
        ]
    },
    {
        "id": "r_004",
        "name": "Запечённая рыба с травами",
        "description": "Белая рыба, запечённая с ароматными травами. "
                       "Отличный источник омега-3 жирных кислот.",
        "calories": 280,
        "proteins": 38,
        "fats": 12,
        "carbs": 2,
        "glycemic_index": 0,
        "purines": 80,
        "cooking_time_min": 35,
        "servings": 2,
        "suitable_for_diabetes": True,
        "suitable_for_gout": True,  # Белая рыба допустима
        "suitable_for_celiac": True,
        "category": "main",
        "ingredients": [
            {"name": "Треска (филе)", "amount": 400, "unit": "г"},
            {"name": "Лимон", "amount": 1, "unit": "шт"},
            {"name": "Чеснок", "amount": 2, "unit": "зубчика"},
            {"name": "Розмарин свежий", "amount": 2, "unit": "веточки"},
            {"name": "Тимьян свежий", "amount": 3, "unit": "веточки"},
            {"name": "Оливковое масло", "amount": 20, "unit": "мл"},
        ],
        "instructions": [
            "Разогреть духовку до 180°C.",
            "Выложить рыбу на фольгу.",
            "Полить оливковым маслом и лимонным соком.",
            "Посыпать мелко нарезанным чесноком.",
            "Положить сверху веточки трав.",
            "Завернуть фольгу, оставив небольшое отверстие.",
            "Запекать 25-30 минут.",
            "Подавать с дольками лимона."
        ]
    },
    {
        "id": "r_005",
        "name": "Овсянка с ягодами и орехами",
        "description": "Полезный завтрак с низким ГИ, богатый клетчаткой "
                       "и антиоксидантами.",
        "calories": 350,
        "proteins": 12,
        "fats": 14,
        "carbs": 48,
        "glycemic_index": 45,
        "purines": 20,
        "cooking_time_min": 15,
        "servings": 1,
        "suitable_for_diabetes": True,
        "suitable_for_gout": True,
        "suitable_for_celiac": False,  # Овёс может содержать глютен
        "category": "breakfast",
        "ingredients": [
            {"name": "Овсяные хлопья (долгой варки)", "amount": 50, "unit": "г"},
            {"name": "Вода или молоко", "amount": 200, "unit": "мл"},
            {"name": "Черника", "amount": 50, "unit": "г"},
            {"name": "Малина", "amount": 50, "unit": "г"},
            {"name": "Грецкие орехи", "amount": 20, "unit": "г"},
            {"name": "Мёд (опционально)", "amount": 5, "unit": "мл"},
        ],
        "instructions": [
            "Залить овсянку водой или молоком.",
            "Варить на среднем огне 10-12 минут, помешивая.",
            "Переложить в тарелку.",
            "Добавить свежие ягоды.",
            "Посыпать измельчёнными орехами.",
            "По желанию добавить немного мёда."
        ]
    },
    {
        "id": "r_006",
        "name": "Творожная запеканка без сахара",
        "description": "Нежная запеканка из творога без добавления сахара. "
                       "Отличный десерт для диабетиков.",
        "calories": 180,
        "proteins": 18,
        "fats": 5,
        "carbs": 15,
        "glycemic_index": 30,
        "purines": 10,
        "cooking_time_min": 45,
        "servings": 4,
        "suitable_for_diabetes": True,
        "suitable_for_gout": True,
        "suitable_for_celiac": False,  # Содержит муку
        "category": "dessert",
        "ingredients": [
            {"name": "Творог 5%", "amount": 500, "unit": "г"},
            {"name": "Яйцо", "amount": 2, "unit": "шт"},
            {"name": "Мука рисовая", "amount": 30, "unit": "г"},
            {"name": "Стевия", "amount": 1, "unit": "ч.л."},
            {"name": "Ванилин", "amount": 1, "unit": "щепотка"},
        ],
        "instructions": [
            "Разогреть духовку до 170°C.",
            "Смешать творог с яйцами.",
            "Добавить муку, стевию и ванилин.",
            "Тщательно перемешать до однородности.",
            "Выложить в смазанную форму.",
            "Запекать 35-40 минут до золотистой корочки.",
            "Остудить перед подачей."
        ]
    },
    {
        "id": "r_007",
        "name": "Суп-пюре из тыквы",
        "description": "Кремовый тыквенный суп с имбирём. "
                       "Низкокалорийный и согревающий.",
        "calories": 120,
        "proteins": 3,
        "fats": 4,
        "carbs": 18,
        "glycemic_index": 65,  # Умеренный ГИ
        "purines": 10,
        "cooking_time_min": 40,
        "servings": 4,
        "suitable_for_diabetes": True,
        "suitable_for_gout": True,
        "suitable_for_celiac": True,
        "category": "soup",
        "ingredients": [
            {"name": "Тыква", "amount": 500, "unit": "г"},
            {"name": "Лук репчатый", "amount": 1, "unit": "шт"},
            {"name": "Имбирь свежий", "amount": 10, "unit": "г"},
            {"name": "Овощной бульон", "amount": 500, "unit": "мл"},
            {"name": "Оливковое масло", "amount": 15, "unit": "мл"},
            {"name": "Тыквенные семечки", "amount": 20, "unit": "г"},
        ],
        "instructions": [
            "Нарезать тыкву кубиками, лук мелко.",
            "Обжарить лук на оливковом масле 3 минуты.",
            "Добавить тыкву и тёртый имбирь.",
            "Залить бульоном и варить 25-30 минут.",
            "Пюрировать блендером до однородности.",
            "Подавать с тыквенными семечками."
        ]
    },
    {
        "id": "r_008",
        "name": "Киноа с овощами",
        "description": "Питательный гарнир из киноа с разноцветными овощами. "
                       "Отличный источник растительного белка.",
        "calories": 280,
        "proteins": 10,
        "fats": 8,
        "carbs": 42,
        "glycemic_index": 35,
        "purines": 20,
        "cooking_time_min": 25,
        "servings": 2,
        "suitable_for_diabetes": True,
        "suitable_for_gout": True,
        "suitable_for_celiac": True,
        "category": "main",
        "ingredients": [
            {"name": "Киноа", "amount": 150, "unit": "г"},
            {"name": "Болгарский перец", "amount": 1, "unit": "шт"},
            {"name": "Помидоры", "amount": 150, "unit": "г"},
            {"name": "Огурец", "amount": 1, "unit": "шт"},
            {"name": "Петрушка", "amount": 30, "unit": "г"},
            {"name": "Лимонный сок", "amount": 30, "unit": "мл"},
            {"name": "Оливковое масло", "amount": 20, "unit": "мл"},
        ],
        "instructions": [
            "Промыть киноа и отварить по инструкции.",
            "Остудить киноа.",
            "Нарезать все овощи мелкими кубиками.",
            "Мелко нарезать петрушку.",
            "Смешать киноа с овощами.",
            "Заправить лимонным соком и оливковым маслом.",
            "Посолить по вкусу."
        ]
    },
    {
        "id": "r_009",
        "name": "Омлет с зеленью и сыром",
        "description": "Белковый завтрак с минимальным содержанием углеводов. "
                       "Быстрое и питательное блюдо.",
        "calories": 250,
        "proteins": 18,
        "fats": 18,
        "carbs": 3,
        "glycemic_index": 0,
        "purines": 15,
        "cooking_time_min": 10,
        "servings": 1,
        "suitable_for_diabetes": True,
        "suitable_for_gout": True,
        "suitable_for_celiac": True,
        "category": "breakfast",
        "ingredients": [
            {"name": "Яйца", "amount": 2, "unit": "шт"},
            {"name": "Молоко", "amount": 30, "unit": "мл"},
            {"name": "Сыр твёрдый", "amount": 30, "unit": "г"},
            {"name": "Шпинат", "amount": 30, "unit": "г"},
            {"name": "Укроп", "amount": 10, "unit": "г"},
            {"name": "Оливковое масло", "amount": 5, "unit": "мл"},
        ],
        "instructions": [
            "Взбить яйца с молоком.",
            "Натереть сыр на тёрке.",
            "Мелко нарезать зелень.",
            "Разогреть масло на сковороде.",
            "Вылить яичную смесь.",
            "Добавить шпинат и зелень.",
            "Посыпать сыром.",
            "Готовить под крышкой 5-7 минут."
        ]
    },
    {
        "id": "r_010",
        "name": "Фасолевый салат с тунцом",
        "description": "Сытный салат с высоким содержанием белка. "
                       "Отличный вариант для обеда.",
        "calories": 320,
        "proteins": 28,
        "fats": 12,
        "carbs": 25,
        "glycemic_index": 25,
        "purines": 150,  # Высокое содержание из-за тунца
        "cooking_time_min": 15,
        "servings": 2,
        "suitable_for_diabetes": True,
        "suitable_for_gout": False,  # Тунец содержит много пуринов
        "suitable_for_celiac": True,
        "category": "salad",
        "ingredients": [
            {"name": "Тунец консервированный", "amount": 150, "unit": "г"},
            {"name": "Фасоль белая (отварная)", "amount": 200, "unit": "г"},
            {"name": "Красный лук", "amount": 50, "unit": "г"},
            {"name": "Помидоры черри", "amount": 100, "unit": "г"},
            {"name": "Петрушка", "amount": 20, "unit": "г"},
            {"name": "Оливковое масло", "amount": 20, "unit": "мл"},
            {"name": "Лимонный сок", "amount": 15, "unit": "мл"},
        ],
        "instructions": [
            "Слить жидкость из тунца, размять вилкой.",
            "Нарезать лук тонкими полукольцами.",
            "Помидоры нарезать пополам.",
            "Мелко нарезать петрушку.",
            "Смешать фасоль, тунец, лук, помидоры.",
            "Добавить петрушку.",
            "Заправить маслом и лимонным соком.",
            "Посолить и поперчить по вкусу."
        ]
    },
]


class RecipeService:
    """
    Сервис для работы с рецептами.

    Предоставляет функционал поиска, фильтрации и получения
    детальной информации о рецептах с учётом медицинских
    диагнозов пользователя.

    Attributes:
        recipes_db: База рецептов для поиска.

    Example:
        >>> service = RecipeService()
        >>> recipes = service.search_recipes("салат", has_gout=True)
        >>> for r in recipes:
        ...     print(r["name"])
    """

    def __init__(self) -> None:
        """
        Инициализирует сервис рецептов.

        Загружает базу рецептов в память для быстрого поиска.
        """
        self.recipes_db = RECIPES_DATABASE
        logger.info(f"Сервис рецептов инициализирован ({len(self.recipes_db)} рецептов)")

    def search_recipes(
        self,
        query: str,
        has_diabetes: bool = False,
        has_gout: bool = False,
        has_celiac: bool = False,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Поиск рецептов по запросу с фильтрацией по диагнозам.

        Ищет рецепты по названию и ингредиентам, затем фильтрует
        по медицинским ограничениям пользователя.

        Args:
            query: Поисковый запрос (название блюда или ингредиент).
            has_diabetes: Фильтровать для диабетиков (ГИ < 55).
            has_gout: Фильтровать для подагры (пурины < 100).
            has_celiac: Фильтровать для целиакии (без глютена).
            limit: Максимальное количество результатов.

        Returns:
            List[Dict]: Список найденных рецептов.

        Example:
            >>> service = RecipeService()
            >>> recipes = service.search_recipes("курица", has_diabetes=True)
        """
        # Нормализуем запрос
        query_lower = query.lower().strip()

        # Ищем по названию и ингредиентам
        matching_recipes = []
        for recipe in self.recipes_db:
            # Проверяем название
            if query_lower in recipe["name"].lower():
                matching_recipes.append(recipe)
                continue

            # Проверяем ингредиенты
            for ingredient in recipe.get("ingredients", []):
                if query_lower in ingredient["name"].lower():
                    matching_recipes.append(recipe)
                    break

        # Применяем фильтрацию по диагнозам
        filtered_recipes = self._filter_by_diagnosis(
            matching_recipes,
            has_diabetes,
            has_gout,
            has_celiac
        )

        logger.info(
            f"Поиск '{query}': найдено {len(filtered_recipes)} рецептов "
            f"(диабет={has_diabetes}, подагра={has_gout}, целиакия={has_celiac})"
        )

        return filtered_recipes[:limit]

    def get_all_recipes(
        self,
        has_diabetes: bool = False,
        has_gout: bool = False,
        has_celiac: bool = False,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Получает все рецепты с фильтрацией.

        Args:
            has_diabetes: Фильтр для диабетиков.
            has_gout: Фильтр для подагры.
            has_celiac: Фильтр для целиакии.
            category: Категория блюда (main, breakfast, salad, soup, dessert).
            limit: Максимальное количество результатов.

        Returns:
            List[Dict]: Список рецептов.

        Example:
            >>> service = RecipeService()
            >>> breakfasts = service.get_all_recipes(category="breakfast")
        """
        recipes = self.recipes_db.copy()

        # Фильтр по категории
        if category:
            recipes = [r for r in recipes if r.get("category") == category]

        # Фильтр по диагнозам
        recipes = self._filter_by_diagnosis(
            recipes,
            has_diabetes,
            has_gout,
            has_celiac
        )

        return recipes[:limit]

    def get_recipe_by_id(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает рецепт по ID.

        Args:
            recipe_id: Уникальный идентификатор рецепта.

        Returns:
            Dict: Информация о рецепте или None если не найден.

        Example:
            >>> service = RecipeService()
            >>> recipe = service.get_recipe_by_id("r_001")
            >>> if recipe:
            ...     print(recipe["name"])
        """
        for recipe in self.recipes_db:
            if recipe["id"] == recipe_id:
                return recipe
        return None

    def get_random_recipe(
        self,
        has_diabetes: bool = False,
        has_gout: bool = False,
        has_celiac: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Получает случайный рецепт с учётом диагнозов.

        Используется для функции "Рецепт дня".

        Args:
            has_diabetes: Учитывать диабет.
            has_gout: Учитывать подагру.
            has_celiac: Учитывать целиакию.

        Returns:
            Dict: Случайный рецепт или None.

        Example:
            >>> service = RecipeService()
            >>> daily_recipe = service.get_random_recipe(has_gout=True)
        """
        filtered = self._filter_by_diagnosis(
            self.recipes_db,
            has_diabetes,
            has_gout,
            has_celiac
        )

        if filtered:
            return random.choice(filtered)
        return None

    def get_recipes_by_category(
        self,
        category: str,
        has_diabetes: bool = False,
        has_gout: bool = False,
        has_celiac: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Получает рецепты по категории.

        Args:
            category: Категория (main, breakfast, salad, soup, dessert).
            has_diabetes: Учитывать диабет.
            has_gout: Учитывать подагру.
            has_celiac: Учитывать целиакию.

        Returns:
            List[Dict]: Список рецептов категории.

        Example:
            >>> service = RecipeService()
            >>> soups = service.get_recipes_by_category("soup")
        """
        category_recipes = [
            r for r in self.recipes_db
            if r.get("category") == category
        ]

        return self._filter_by_diagnosis(
            category_recipes,
            has_diabetes,
            has_gout,
            has_celiac
        )

    def _filter_by_diagnosis(
        self,
        recipes: List[Dict[str, Any]],
        has_diabetes: bool,
        has_gout: bool,
        has_celiac: bool
    ) -> List[Dict[str, Any]]:
        """
        Фильтрует рецепты по медицинским диагнозам.

        Применяет строгие критерии фильтрации:
        - Диабет: ГИ < max_glycemic_index (по умолчанию 55)
        - Подагра: Пурины < 100 мг/100г
        - Целиакия: suitable_for_celiac == True

        Args:
            recipes: Список рецептов для фильтрации.
            has_diabetes: Наличие диабета.
            has_gout: Наличие подагры.
            has_celiac: Наличие целиакии.

        Returns:
            List[Dict]: Отфильтрованный список рецептов.
        """
        filtered = []

        for recipe in recipes:
            # Проверка для диабета (ГИ)
            if has_diabetes:
                gi = recipe.get("glycemic_index", 0)
                if gi > settings.max_glycemic_index:
                    continue

            # Проверка для подагры (пурины)
            if has_gout:
                purines = recipe.get("purines", 0)
                if purines > 100:  # Лимит пуринов для подагры
                    continue

            # Проверка для целиакии (глютен)
            if has_celiac:
                if not recipe.get("suitable_for_celiac", False):
                    continue

            filtered.append(recipe)

        return filtered

    def format_recipe_for_display(self, recipe: Dict[str, Any]) -> str:
        """
        Форматирует рецепт для отображения в Telegram.

        Args:
            recipe: Словарь с информацией о рецепте.

        Returns:
            str: Форматированная строка для отправки в Telegram.

        Example:
            >>> service = RecipeService()
            >>> recipe = service.get_recipe_by_id("r_001")
            >>> text = service.format_recipe_for_display(recipe)
            >>> print(text)
        """
        # Формируем заголовок
        text = f"<b>{recipe['name']}</b>\n\n"

        # Описание
        if recipe.get("description"):
            text += f"{recipe['description']}\n\n"

        # Время и порции
        text += (
            f"Время: {recipe.get('cooking_time_min', 'N/A')} мин | "
            f"Порций: {recipe.get('servings', 'N/A')}\n\n"
        )

        # Пищевая ценность
        text += (
            f"<b>Пищевая ценность (на порцию):</b>\n"
            f"Калории: {recipe.get('calories', 0)} ккал\n"
            f"Белки: {recipe.get('proteins', 0)} г | "
            f"Жиры: {recipe.get('fats', 0)} г | "
            f"Углеводы: {recipe.get('carbs', 0)} г\n"
            f"ГИ: {recipe.get('glycemic_index', 'N/A')} | "
            f"Пурины: {recipe.get('purines', 'N/A')} мг\n\n"
        )

        # Ингредиенты
        text += "<b>Ингредиенты:</b>\n"
        for ing in recipe.get("ingredients", []):
            text += f"• {ing['name']}: {ing['amount']} {ing['unit']}\n"

        text += "\n<b>Приготовление:</b>\n"
        for i, step in enumerate(recipe.get("instructions", []), 1):
            text += f"{i}. {step}\n"

        return text
