#!/usr/bin/env python3
"""
MedMarket Bot - Точка входа приложения.

Этот модуль является главной точкой входа для Telegram бота MedMarket.
Инициализирует все компоненты и запускает polling или webhook
в зависимости от конфигурации.

Модуль соответствует стандартам PEP8 и PEP257.

Usage:
    Запуск бота::

        $ python main.py

    Или через Docker::

        $ docker run medmarket-bot

Author: MedMarket Team
License: MIT
Version: 1.0.0
"""

import sys
from pathlib import Path

import telebot
from loguru import logger

# =============================================================================
# НАСТРОЙКА ПУТЕЙ И ЛОГИРОВАНИЯ
# =============================================================================

# Добавляем корневую директорию проекта в PATH
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Настраиваем логирование перед импортом других модулей
logger.remove()  # Удаляем стандартный обработчик

# Консольный вывод
logger.add(
    sys.stdout,
    format=(
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
    level="INFO",
    colorize=True
)

# Файловый лог для production
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger.add(
    str(LOG_DIR / "bot.log"),
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="500 MB",
    retention="7 days",
    compression="zip"
)

# =============================================================================
# ИМПОРТ МОДУЛЕЙ ПРИЛОЖЕНИЯ
# =============================================================================

from config import settings, validate_critical_settings  # noqa: E402
from database import init_db  # noqa: E402
from handlers import register_handlers  # noqa: E402
from middleware import setup_middleware  # noqa: E402


# =============================================================================
# ИНИЦИАЛИЗАЦИЯ БОТА
# =============================================================================

def create_bot() -> telebot.TeleBot:
    """
    Создаёт и настраивает экземпляр Telegram бота.

    Инициализирует бота с токеном из настроек и настраивает
    базовые параметры.

    Returns:
        telebot.TeleBot: Настроенный экземпляр бота.

    Raises:
        ValueError: Если TELEGRAM_BOT_TOKEN не установлен.

    Example:
        >>> bot = create_bot()
        >>> bot.infinity_polling()
    """
    # Валидируем критические настройки
    validate_critical_settings()

    # Создаём экземпляр бота
    bot = telebot.TeleBot(
        token=settings.telegram_bot_token,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

    logger.info(
        f"Telegram бот инициализирован: "
        f"{settings.telegram_bot_token[:10]}..."
    )

    return bot


def initialize_components(bot: telebot.TeleBot) -> None:
    """
    Инициализирует все компоненты приложения.

    Последовательно инициализирует:
    1. База данных (создание таблиц)
    2. Middleware (логирование, rate limiting)
    3. Обработчики команд и сообщений

    Args:
        bot: Экземпляр Telegram бота.

    Raises:
        Exception: При ошибке инициализации любого компонента.

    Example:
        >>> bot = create_bot()
        >>> initialize_components(bot)
    """
    # 1. Инициализация базы данных
    logger.info("Инициализация базы данных...")
    init_db()
    logger.info("База данных готова")

    # 2. Настройка middleware
    logger.info("Настройка middleware...")
    try:
        setup_middleware(bot)
    except Exception as exc:
        logger.warning(f"Middleware не настроена: {exc}")

    # 3. Регистрация обработчиков
    logger.info("Регистрация обработчиков...")
    register_handlers(bot)
    logger.info("Обработчики зарегистрированы")


def run_polling(bot: telebot.TeleBot) -> None:
    """
    Запускает бота в режиме polling.

    Polling - режим работы, при котором бот периодически опрашивает
    серверы Telegram на наличие новых сообщений. Подходит для
    разработки и небольших нагрузок.

    Args:
        bot: Экземпляр Telegram бота.

    Note:
        Для production рекомендуется использовать webhook.

    Example:
        >>> bot = create_bot()
        >>> initialize_components(bot)
        >>> run_polling(bot)
    """
    logger.info(
        f"Запуск бота в режиме POLLING | "
        f"Timeout: {settings.polling_timeout}с"
    )

    try:
        # Запускаем бесконечный polling
        bot.infinity_polling(
            timeout=settings.polling_timeout,
            long_polling_timeout=30,
            logger_level=None,  # Отключаем внутреннее логирование telebot
            skip_pending=True  # Пропускаем накопившиеся сообщения при старте
        )

    except KeyboardInterrupt:
        logger.warning("Получен сигнал прерывания (Ctrl+C)")
        logger.info("Бот остановлен пользователем")
        sys.exit(0)

    except Exception as exc:
        logger.critical(f"Критическая ошибка бота: {exc}", exc_info=True)
        sys.exit(1)


def main() -> None:
    """
    Главная функция приложения.

    Последовательность запуска:
    1. Вывод информации о версии
    2. Создание экземпляра бота
    3. Инициализация всех компонентов
    4. Запуск polling

    Example:
        >>> if __name__ == "__main__":
        ...     main()
    """
    # Выводим информацию о запуске
    logger.info("=" * 60)
    logger.info(
        f"{settings.app_name} v{settings.app_version} запускается"
    )
    logger.info(f"Окружение: {settings.environment}")
    logger.info(f"Debug: {settings.debug}")
    logger.info("=" * 60)

    try:
        # Создаём бота
        bot = create_bot()

        # Инициализируем компоненты
        initialize_components(bot)

        logger.info("Все компоненты готовы")
        logger.info("Запуск polling...")

        # Запускаем бота
        run_polling(bot)

    except ValueError as exc:
        logger.error(f"Ошибка конфигурации: {exc}")
        sys.exit(1)

    except Exception as exc:
        logger.critical(f"Не удалось запустить бота: {exc}", exc_info=True)
        sys.exit(1)


# =============================================================================
# ТОЧКА ВХОДА
# =============================================================================

if __name__ == "__main__":
    main()
