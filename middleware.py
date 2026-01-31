"""
MedMarket Bot - Модуль middleware.

Этот модуль содержит middleware для обработки сообщений,
логирования и проверки пользователей перед основными обработчиками.

Модуль соответствует стандартам PEP8 и PEP257.

Example:
    Настройка middleware::

        from middleware import setup_middleware
        setup_middleware(bot)

Author: MedMarket Team
License: MIT
Version: 1.0.0
"""

import time
from functools import wraps
from typing import Any, Callable

import telebot
from loguru import logger


def setup_middleware(bot: telebot.TeleBot) -> None:
    """
    Настраивает middleware для бота.

    Добавляет логирование всех входящих сообщений и callback'ов.

    Args:
        bot: Экземпляр Telegram бота.

    Example:
        >>> bot = telebot.TeleBot(token)
        >>> setup_middleware(bot)
    """

    class LoggingMiddleware(telebot.handler_backends.BaseMiddleware):
        """
        Middleware для логирования всех входящих обновлений.

        Логирует информацию о пользователе, типе сообщения и времени обработки.
        """

        def __init__(self) -> None:
            """Инициализирует middleware."""
            self.update_types = ["message", "callback_query"]

        def pre_process(self, message: Any, data: dict) -> None:
            """
            Предобработка перед основным обработчиком.

            Логирует входящее сообщение и сохраняет время начала обработки.

            Args:
                message: Объект сообщения или callback.
                data: Словарь для передачи данных между middleware.
            """
            data["start_time"] = time.time()

            # Определяем тип обновления
            if hasattr(message, "text"):
                # Это сообщение
                user_id = message.from_user.id
                username = message.from_user.username or "unknown"
                text = message.text[:30] + "..." if message.text and len(message.text) > 30 else message.text

                logger.info(
                    f"Сообщение от @{username} ({user_id}): {text}"
                )

            elif hasattr(message, "data"):
                # Это callback
                user_id = message.from_user.id
                username = message.from_user.username or "unknown"

                logger.info(
                    f"Callback от @{username} ({user_id}): {message.data}"
                )

        def post_process(
            self,
            message: Any,
            data: dict,
            exception: Exception = None
        ) -> None:
            """
            Постобработка после основного обработчика.

            Логирует время обработки и ошибки, если они произошли.

            Args:
                message: Объект сообщения или callback.
                data: Словарь с данными от pre_process.
                exception: Исключение, если произошла ошибка.
            """
            # Вычисляем время обработки
            elapsed_time = time.time() - data.get("start_time", time.time())

            if exception:
                logger.error(
                    f"Ошибка обработки ({elapsed_time:.3f}с): {exception}"
                )
            else:
                # Логируем только если обработка заняла больше 1 секунды
                if elapsed_time > 1.0:
                    logger.warning(
                        f"Медленная обработка: {elapsed_time:.3f}с"
                    )

    # Включаем middleware
    bot.setup_middleware(LoggingMiddleware())

    logger.info("Middleware настроена")


def rate_limit(calls: int = 5, period: int = 60) -> Callable:
    """
    Декоратор для ограничения частоты вызовов функции.

    Предотвращает спам и защищает от DoS атак.

    Args:
        calls: Максимальное количество вызовов.
        period: Период в секундах.

    Returns:
        Callable: Декорированная функция.

    Example:
        >>> @rate_limit(calls=3, period=60)
        ... def send_message(user_id):
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        # Словарь для хранения истории вызовов
        call_history: dict = {}

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Получаем user_id из аргументов
            user_id = None
            if args:
                message = args[0]
                if hasattr(message, "from_user"):
                    user_id = message.from_user.id

            if user_id:
                current_time = time.time()

                # Инициализируем историю для пользователя
                if user_id not in call_history:
                    call_history[user_id] = []

                # Очищаем старые записи
                call_history[user_id] = [
                    t for t in call_history[user_id]
                    if current_time - t < period
                ]

                # Проверяем лимит
                if len(call_history[user_id]) >= calls:
                    logger.warning(
                        f"Rate limit для пользователя {user_id}"
                    )
                    return None

                # Добавляем текущий вызов
                call_history[user_id].append(current_time)

            return func(*args, **kwargs)

        return wrapper

    return decorator


def log_execution_time(func: Callable) -> Callable:
    """
    Декоратор для логирования времени выполнения функции.

    Args:
        func: Функция для декорирования.

    Returns:
        Callable: Декорированная функция.

    Example:
        >>> @log_execution_time
        ... def process_data():
        ...     pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time

        logger.debug(
            f"{func.__name__} выполнена за {elapsed:.3f}с"
        )

        return result

    return wrapper


def handle_exceptions(func: Callable) -> Callable:
    """
    Декоратор для обработки исключений.

    Логирует ошибки и возвращает None вместо падения.

    Args:
        func: Функция для декорирования.

    Returns:
        Callable: Декорированная функция.

    Example:
        >>> @handle_exceptions
        ... def risky_operation():
        ...     pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            logger.error(
                f"Ошибка в {func.__name__}: {exc}",
                exc_info=True
            )
            return None

    return wrapper
