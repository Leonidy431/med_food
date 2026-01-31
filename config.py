"""
MedMarket Bot - Модуль конфигурации.

Этот модуль содержит настройки приложения с использованием Pydantic.
Автоматически загружает переменные окружения из .env файла
и валидирует их при запуске.

Модуль соответствует стандартам PEP8 и PEP257 для документации.

Example:
    Использование настроек в других модулях::

        from config import settings
        token = settings.telegram_bot_token

Attributes:
    settings (Settings): Глобальный объект настроек приложения.

Author: MedMarket Team
License: MIT
Version: 1.0.0
"""

import os
from functools import lru_cache
from typing import Literal, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Основные настройки приложения.

    Класс загружает конфигурацию из переменных окружения и .env файла.
    Использует Pydantic для валидации и типизации значений.

    Attributes:
        app_name: Название приложения.
        app_version: Версия приложения.
        environment: Тип окружения (development, production, testing).
        debug: Режим отладки (включает подробное логирование SQL).
        telegram_bot_token: Токен Telegram бота от @BotFather.
        polling_timeout: Таймаут между запросами к Telegram API (секунды).
        telegram_api_server: URL сервера Telegram API.
        database_url: URL подключения к PostgreSQL базе данных.
        openai_api_key: API ключ OpenAI для GPT-4 диетолога.
        google_maps_api_key: API ключ Google Maps для геолокации.
        redis_url: URL Redis для кэширования (опционально).
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        max_recipe_results: Максимальное количество рецептов в результатах.
        max_shops_results: Максимальное количество магазинов в результатах.
        daily_purines_limit: Суточный лимит пуринов для подагры (мг).
        max_glycemic_index: Максимальный ГИ для диабета.

    Example:
        >>> from config import settings
        >>> print(settings.app_name)
        MedMarket Bot
    """

    # =========================================================================
    # ОСНОВНЫЕ НАСТРОЙКИ ПРИЛОЖЕНИЯ
    # =========================================================================

    app_name: str = "MedMarket Bot"
    app_version: str = "1.0.0"
    environment: Literal["development", "production", "testing"] = "development"
    debug: bool = False

    # =========================================================================
    # TELEGRAM НАСТРОЙКИ
    # =========================================================================

    telegram_bot_token: str = ""
    polling_timeout: int = 60
    telegram_api_server: str = "https://api.telegram.org"

    # =========================================================================
    # БАЗА ДАННЫХ (Railway автоматически создаёт DATABASE_URL)
    # =========================================================================

    database_url: str = "sqlite:///./medmarket.db"

    # =========================================================================
    # ВНЕШНИЕ API КЛЮЧИ
    # =========================================================================

    openai_api_key: str = ""
    google_maps_api_key: str = ""

    # =========================================================================
    # REDIS НАСТРОЙКИ (опционально)
    # =========================================================================

    redis_url: str = "redis://localhost:6379/0"

    # =========================================================================
    # ЛОГИРОВАНИЕ
    # =========================================================================

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # =========================================================================
    # ЛИМИТЫ ПОИСКА
    # =========================================================================

    max_recipe_results: int = 10
    max_shops_results: int = 5

    # =========================================================================
    # МЕДИЦИНСКИЕ ЛИМИТЫ
    # =========================================================================

    daily_purines_limit: int = 200  # мг/день для подагры
    max_glycemic_index: int = 55  # Низкий ГИ для диабета

    class Config:
        """
        Конфигурация Pydantic модели.

        Attributes:
            env_file: Путь к файлу с переменными окружения.
            env_file_encoding: Кодировка .env файла.
            case_sensitive: Чувствительность к регистру переменных.
            extra: Политика обработки дополнительных полей.
        """

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Игнорируем неизвестные переменные


@lru_cache()
def get_settings() -> Settings:
    """
    Получает и кэширует настройки приложения.

    Функция использует LRU-кэширование для оптимизации производительности.
    При первом вызове загружает настройки из окружения, при последующих
    возвращает закэшированный объект.

    Returns:
        Settings: Объект настроек с загруженными параметрами.

    Example:
        >>> settings = get_settings()
        >>> print(settings.app_name)
        MedMarket Bot
    """
    return Settings()


# Глобальный объект настроек для импорта в других модулях
settings = get_settings()


def validate_critical_settings() -> bool:
    """
    Валидирует критические настройки приложения.

    Проверяет наличие обязательных API ключей и конфигурации,
    необходимых для работы бота.

    Returns:
        bool: True если все критические настройки установлены.

    Raises:
        ValueError: Если отсутствуют критические переменные окружения.

    Example:
        >>> try:
        ...     validate_critical_settings()
        ... except ValueError as e:
        ...     print(f"Ошибка: {e}")
    """
    missing_vars = []

    if not settings.telegram_bot_token:
        missing_vars.append("TELEGRAM_BOT_TOKEN")

    if missing_vars:
        raise ValueError(
            f"Отсутствуют критические переменные окружения: "
            f"{', '.join(missing_vars)}. "
            f"Установите их в .env файле или переменных Railway."
        )

    return True


def is_production() -> bool:
    """
    Проверяет, запущено ли приложение в production окружении.

    Returns:
        bool: True если environment == "production".

    Example:
        >>> if is_production():
        ...     print("Production mode")
    """
    return settings.environment == "production"


def is_development() -> bool:
    """
    Проверяет, запущено ли приложение в development окружении.

    Returns:
        bool: True если environment == "development".

    Example:
        >>> if is_development():
        ...     print("Development mode")
    """
    return settings.environment == "development"
