"""
MedMarket Bot - Сервис магазинов.

Этот модуль содержит сервис для поиска ближайших магазинов
и сравнения цен на продукты. Поддерживает интеграцию
с Google Maps API и маркетплейсами.

Модуль соответствует стандартам PEP8 и PEP257.

Example:
    Использование сервиса::

        from services.shop_service import ShopService

        service = ShopService()
        shops = service.find_nearby_shops(55.7558, 37.6173, radius_km=2.0)
        for shop in shops:
            print(f"{shop['name']}: {shop['distance_km']} км")

Author: MedMarket Team
License: MIT
Version: 1.0.0
"""

import math
from typing import Any, Dict, List, Optional

from loguru import logger

from config import settings


# =============================================================================
# БАЗА ДАННЫХ МАГАЗИНОВ (MOCK DATA)
# =============================================================================

# Тестовые данные магазинов для демонстрации
# В продакшене заменяется на Google Places API
MOCK_SHOPS: List[Dict[str, Any]] = [
    {
        "id": "shop_001",
        "name": "Пятёрочка",
        "chain": "X5 Retail Group",
        "latitude": 55.7558,
        "longitude": 37.6173,
        "address": "Москва, Красная площадь, 1",
        "rating": 4.7,
        "working_hours": "08:00-23:00",
        "has_delivery": True
    },
    {
        "id": "shop_002",
        "name": "Магнит",
        "chain": "Магнит",
        "latitude": 55.7500,
        "longitude": 37.6200,
        "address": "Москва, ул. Тверская, 15",
        "rating": 4.5,
        "working_hours": "07:00-23:00",
        "has_delivery": True
    },
    {
        "id": "shop_003",
        "name": "Дикси",
        "chain": "Дикси",
        "latitude": 55.7600,
        "longitude": 37.6100,
        "address": "Москва, Охотный ряд, 2",
        "rating": 4.3,
        "working_hours": "06:00-23:00",
        "has_delivery": False
    },
    {
        "id": "shop_004",
        "name": "ВкусВилл",
        "chain": "ВкусВилл",
        "latitude": 55.7520,
        "longitude": 37.6150,
        "address": "Москва, ул. Никольская, 10",
        "rating": 4.8,
        "working_hours": "08:00-22:00",
        "has_delivery": True
    },
    {
        "id": "shop_005",
        "name": "Перекрёсток",
        "chain": "X5 Retail Group",
        "latitude": 55.7580,
        "longitude": 37.6220,
        "address": "Москва, ул. Петровка, 5",
        "rating": 4.6,
        "working_hours": "07:00-24:00",
        "has_delivery": True
    },
]

# Примерные цены на продукты в разных магазинах
MOCK_PRICES: Dict[str, Dict[str, float]] = {
    "shop_001": {  # Пятёрочка
        "Куриное филе": 289,
        "Брокколи": 149,
        "Гречневая крупа": 89,
        "Оливковое масло": 549,
        "Творог 5%": 89,
        "Яйца (10 шт)": 99,
        "Овсяные хлопья": 79,
        "Треска (филе)": 449,
        "Помидоры черри": 199,
        "Киноа": 299,
    },
    "shop_002": {  # Магнит
        "Куриное филе": 279,
        "Брокколи": 159,
        "Гречневая крупа": 79,
        "Оливковое масло": 529,
        "Творог 5%": 79,
        "Яйца (10 шт)": 89,
        "Овсяные хлопья": 69,
        "Треска (филе)": 429,
        "Помидоры черри": 189,
        "Киноа": 319,
    },
    "shop_003": {  # Дикси
        "Куриное филе": 299,
        "Брокколи": 139,
        "Гречневая крупа": 85,
        "Оливковое масло": 569,
        "Творог 5%": 85,
        "Яйца (10 шт)": 95,
        "Овсяные хлопья": 75,
        "Треска (филе)": 459,
        "Помидоры черри": 179,
        "Киноа": 289,
    },
    "shop_004": {  # ВкусВилл
        "Куриное филе": 329,
        "Брокколи": 169,
        "Гречневая крупа": 99,
        "Оливковое масло": 599,
        "Творог 5%": 99,
        "Яйца (10 шт)": 129,
        "Овсяные хлопья": 89,
        "Треска (филе)": 499,
        "Помидоры черри": 229,
        "Киноа": 349,
    },
    "shop_005": {  # Перекрёсток
        "Куриное филе": 309,
        "Брокколи": 159,
        "Гречневая крупа": 95,
        "Оливковое масло": 579,
        "Творог 5%": 95,
        "Яйца (10 шт)": 109,
        "Овсяные хлопья": 85,
        "Треска (филе)": 479,
        "Помидоры черри": 209,
        "Киноа": 329,
    },
}


class ShopService:
    """
    Сервис для работы с магазинами и ценами.

    Предоставляет функционал поиска ближайших магазинов,
    сравнения цен и расчёта стоимости рецептов.

    Attributes:
        shops_db: База данных магазинов.
        prices_db: База данных цен.

    Example:
        >>> service = ShopService()
        >>> shops = service.find_nearby_shops(55.75, 37.62)
        >>> cheapest = service.find_cheapest_shop_for_product("Гречка")
    """

    # Константы для расчёта расстояния
    EARTH_RADIUS_KM = 6371.0  # Радиус Земли в км

    def __init__(self) -> None:
        """
        Инициализирует сервис магазинов.

        Загружает базы данных магазинов и цен.
        """
        self.shops_db = MOCK_SHOPS
        self.prices_db = MOCK_PRICES
        logger.info(
            f"Сервис магазинов инициализирован "
            f"({len(self.shops_db)} магазинов)"
        )

    def find_nearby_shops(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 2.0,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Находит ближайшие магазины по геолокации.

        Использует формулу Гаверсина для точного расчёта
        расстояния между координатами.

        Args:
            latitude: Широта пользователя.
            longitude: Долгота пользователя.
            radius_km: Радиус поиска в километрах.
            limit: Максимальное количество результатов.

        Returns:
            List[Dict]: Список магазинов с расстояниями, отсортированный
                        по близости.

        Example:
            >>> service = ShopService()
            >>> shops = service.find_nearby_shops(55.7558, 37.6173)
            >>> for shop in shops:
            ...     print(f"{shop['name']}: {shop['distance_km']} км")
        """
        shops_with_distance = []

        for shop in self.shops_db:
            # Вычисляем расстояние по формуле Гаверсина
            distance = self._calculate_haversine_distance(
                latitude,
                longitude,
                shop["latitude"],
                shop["longitude"]
            )

            # Фильтруем по радиусу
            if distance <= radius_km:
                shop_data = shop.copy()
                shop_data["distance_km"] = round(distance, 2)
                shops_with_distance.append(shop_data)

        # Сортируем по расстоянию
        shops_with_distance.sort(key=lambda x: x["distance_km"])

        logger.info(
            f"Найдено {len(shops_with_distance)} магазинов "
            f"в радиусе {radius_km} км от ({latitude}, {longitude})"
        )

        return shops_with_distance[:limit]

    def get_prices_for_recipe(
        self,
        recipe_ingredients: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Получает цены на ингредиенты рецепта во всех магазинах.

        Args:
            recipe_ingredients: Список ингредиентов рецепта.

        Returns:
            Dict: Цены по магазинам с общей стоимостью.

        Example:
            >>> service = ShopService()
            >>> ingredients = [{"name": "Куриное филе"}, {"name": "Брокколи"}]
            >>> prices = service.get_prices_for_recipe(ingredients)
        """
        prices_by_shop = {}

        for shop in self.shops_db:
            shop_id = shop["id"]
            shop_prices = self.prices_db.get(shop_id, {})

            total_price = 0.0
            found_count = 0
            items_prices = []

            for ingredient in recipe_ingredients:
                ingredient_name = ingredient.get("name", "")
                # Ищем точное или частичное совпадение
                price = self._find_product_price(shop_prices, ingredient_name)

                if price is not None:
                    total_price += price
                    found_count += 1
                    items_prices.append({
                        "name": ingredient_name,
                        "price": price
                    })

            prices_by_shop[shop_id] = {
                "shop_name": shop["name"],
                "shop_address": shop["address"],
                "total_price": total_price,
                "found_items": found_count,
                "total_items": len(recipe_ingredients),
                "items": items_prices,
                "rating": shop["rating"]
            }

        return prices_by_shop

    def find_cheapest_shop_for_product(
        self,
        product_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Находит магазин с минимальной ценой на продукт.

        Args:
            product_name: Название продукта.

        Returns:
            Dict: Информация о магазине с лучшей ценой или None.

        Example:
            >>> service = ShopService()
            >>> result = service.find_cheapest_shop_for_product("Гречневая крупа")
            >>> print(f"{result['shop_name']}: {result['price']} руб.")
        """
        best_shop = None
        best_price = float("inf")

        for shop in self.shops_db:
            shop_id = shop["id"]
            shop_prices = self.prices_db.get(shop_id, {})
            price = self._find_product_price(shop_prices, product_name)

            if price is not None and price < best_price:
                best_price = price
                best_shop = {
                    "shop_id": shop_id,
                    "shop_name": shop["name"],
                    "shop_address": shop["address"],
                    "price": price,
                    "rating": shop["rating"]
                }

        if best_shop:
            logger.info(
                f"Лучшая цена на '{product_name}': "
                f"{best_shop['shop_name']} - {best_shop['price']} руб."
            )

        return best_shop

    def find_cheapest_shop_for_recipe(
        self,
        recipe_ingredients: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Находит магазин с минимальной общей стоимостью рецепта.

        Args:
            recipe_ingredients: Список ингредиентов рецепта.

        Returns:
            Dict: Информация о самом выгодном магазине.

        Example:
            >>> service = ShopService()
            >>> ingredients = [{"name": "Курица"}, {"name": "Овощи"}]
            >>> result = service.find_cheapest_shop_for_recipe(ingredients)
        """
        prices_by_shop = self.get_prices_for_recipe(recipe_ingredients)

        if not prices_by_shop:
            return None

        # Находим магазин с минимальной общей стоимостью
        cheapest = min(
            prices_by_shop.items(),
            key=lambda x: x[1]["total_price"] if x[1]["total_price"] > 0 else float("inf")
        )

        shop_id, shop_data = cheapest
        shop_data["shop_id"] = shop_id

        logger.info(
            f"Самый выгодный магазин: {shop_data['shop_name']} - "
            f"{shop_data['total_price']} руб."
        )

        return shop_data

    def compare_prices(
        self,
        product_name: str
    ) -> List[Dict[str, Any]]:
        """
        Сравнивает цены на продукт во всех магазинах.

        Args:
            product_name: Название продукта.

        Returns:
            List[Dict]: Список магазинов с ценами, отсортированный
                        по возрастанию цены.

        Example:
            >>> service = ShopService()
            >>> comparison = service.compare_prices("Оливковое масло")
            >>> for item in comparison:
            ...     print(f"{item['shop_name']}: {item['price']} руб.")
        """
        results = []

        for shop in self.shops_db:
            shop_id = shop["id"]
            shop_prices = self.prices_db.get(shop_id, {})
            price = self._find_product_price(shop_prices, product_name)

            if price is not None:
                results.append({
                    "shop_id": shop_id,
                    "shop_name": shop["name"],
                    "shop_address": shop["address"],
                    "price": price,
                    "rating": shop["rating"]
                })

        # Сортируем по цене
        results.sort(key=lambda x: x["price"])

        return results

    def get_shop_by_id(self, shop_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о магазине по ID.

        Args:
            shop_id: Идентификатор магазина.

        Returns:
            Dict: Информация о магазине или None.

        Example:
            >>> service = ShopService()
            >>> shop = service.get_shop_by_id("shop_001")
        """
        for shop in self.shops_db:
            if shop["id"] == shop_id:
                return shop
        return None

    def format_prices_for_display(
        self,
        prices_comparison: List[Dict[str, Any]],
        product_name: str
    ) -> str:
        """
        Форматирует сравнение цен для отображения в Telegram.

        Args:
            prices_comparison: Результат сравнения цен.
            product_name: Название продукта.

        Returns:
            str: Форматированная строка для Telegram.

        Example:
            >>> service = ShopService()
            >>> comparison = service.compare_prices("Гречка")
            >>> text = service.format_prices_for_display(comparison, "Гречка")
        """
        if not prices_comparison:
            return f"Цены на '{product_name}' не найдены."

        text = f"<b>Сравнение цен: {product_name}</b>\n\n"

        for i, item in enumerate(prices_comparison, 1):
            # Эмодзи для топ-3
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = f"{i}."

            text += (
                f"{emoji} <b>{item['shop_name']}</b>\n"
                f"   Цена: {item['price']} руб.\n"
                f"   {item['shop_address']}\n\n"
            )

        # Считаем экономию
        if len(prices_comparison) >= 2:
            savings = prices_comparison[-1]["price"] - prices_comparison[0]["price"]
            if savings > 0:
                text += f"💡 Экономия: до {savings} руб."

        return text

    def format_shops_for_display(
        self,
        shops: List[Dict[str, Any]]
    ) -> str:
        """
        Форматирует список магазинов для отображения в Telegram.

        Args:
            shops: Список магазинов с расстояниями.

        Returns:
            str: Форматированная строка для Telegram.

        Example:
            >>> service = ShopService()
            >>> shops = service.find_nearby_shops(55.75, 37.62)
            >>> text = service.format_shops_for_display(shops)
        """
        if not shops:
            return "Магазины поблизости не найдены."

        text = "<b>Магазины поблизости:</b>\n\n"

        for shop in shops:
            # Звёздочки рейтинга
            stars = "⭐" * int(shop.get("rating", 0))

            text += (
                f"<b>{shop['name']}</b> ({shop['distance_km']} км)\n"
                f"📍 {shop['address']}\n"
                f"🕐 {shop.get('working_hours', 'N/A')}\n"
                f"Рейтинг: {stars} ({shop.get('rating', 'N/A')})\n"
            )

            if shop.get("has_delivery"):
                text += "🚚 Доставка доступна\n"

            text += "\n"

        return text

    def _calculate_haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Вычисляет расстояние между двумя точками по формуле Гаверсина.

        Формула Гаверсина учитывает кривизну Земли и даёт
        точный результат для любых расстояний.

        Args:
            lat1: Широта первой точки.
            lon1: Долгота первой точки.
            lat2: Широта второй точки.
            lon2: Долгота второй точки.

        Returns:
            float: Расстояние в километрах.

        Example:
            >>> service = ShopService()
            >>> distance = service._calculate_haversine_distance(
            ...     55.7558, 37.6173, 55.7500, 37.6200
            ... )
        """
        # Преобразуем градусы в радианы
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        # Формула Гаверсина
        a = (
            math.sin(delta_lat / 2) ** 2 +
            math.cos(lat1_rad) * math.cos(lat2_rad) *
            math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = self.EARTH_RADIUS_KM * c
        return distance

    def _find_product_price(
        self,
        shop_prices: Dict[str, float],
        product_name: str
    ) -> Optional[float]:
        """
        Ищет цену продукта в базе магазина.

        Поддерживает точное и частичное совпадение названий.

        Args:
            shop_prices: Словарь цен магазина.
            product_name: Название искомого продукта.

        Returns:
            float: Цена продукта или None если не найден.
        """
        product_lower = product_name.lower()

        # Сначала ищем точное совпадение
        for name, price in shop_prices.items():
            if name.lower() == product_lower:
                return price

        # Затем частичное совпадение
        for name, price in shop_prices.items():
            if product_lower in name.lower() or name.lower() in product_lower:
                return price

        return None
