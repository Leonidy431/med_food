"""
MedMarket Bot - Модуль обработчиков команд.

Этот модуль содержит все обработчики команд и сообщений Telegram бота.
Включает главное меню, поиск рецептов, AI-диетолога, работу с дневником
питания и списком покупок.

Модуль соответствует стандартам PEP8 и PEP257.

Example:
    Регистрация обработчиков::

        from handlers import register_handlers
        register_handlers(bot)

Author: MedMarket Team
License: MIT
Version: 1.0.0
"""

from datetime import datetime
from typing import Dict, Optional

import telebot
from loguru import logger
from telebot.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import settings
from database import (
    SessionLocal,
    User,
    UserDiary,
    ShoppingList,
    get_or_create_user,
)
from services.gpt_service import GPTService
from services.recipe_service import RecipeService
from services.shop_service import ShopService


# =============================================================================
# ИНИЦИАЛИЗАЦИЯ СЕРВИСОВ
# =============================================================================

# Создаём экземпляры сервисов один раз при загрузке модуля
recipe_service = RecipeService()
gpt_service = GPTService()
shop_service = ShopService()


# =============================================================================
# ХРАНИЛИЩЕ СОСТОЯНИЙ ПОЛЬЗОВАТЕЛЕЙ (FSM)
# =============================================================================

# Словарь для хранения состояний пользователей
# Ключ: telegram_id, Значение: словарь с состоянием и данными
user_states: Dict[int, Dict[str, str]] = {}


# =============================================================================
# КЛАВИАТУРЫ
# =============================================================================

def create_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт клавиатуру главного меню.

    Returns:
        InlineKeyboardMarkup: Инлайн-клавиатура с кнопками меню.

    Example:
        >>> keyboard = create_main_menu_keyboard()
        >>> bot.send_message(chat_id, "Меню", reply_markup=keyboard)
    """
    keyboard = InlineKeyboardMarkup(row_width=2)

    # Первый ряд - основные функции
    keyboard.add(
        InlineKeyboardButton(
            text="🔍 Поиск рецептов",
            callback_data="search_recipes"
        ),
        InlineKeyboardButton(
            text="🍽 Рецепт дня",
            callback_data="daily_recipe"
        )
    )

    # Второй ряд
    keyboard.add(
        InlineKeyboardButton(
            text="📍 Магазины рядом",
            callback_data="find_shops"
        ),
        InlineKeyboardButton(
            text="💰 Сравнить цены",
            callback_data="compare_prices"
        )
    )

    # Третий ряд
    keyboard.add(
        InlineKeyboardButton(
            text="📔 Мой дневник",
            callback_data="view_diary"
        ),
        InlineKeyboardButton(
            text="🛒 Список покупок",
            callback_data="shopping_list"
        )
    )

    # Четвёртый ряд
    keyboard.add(
        InlineKeyboardButton(
            text="🤖 AI-диетолог",
            callback_data="ask_dietician"
        ),
        InlineKeyboardButton(
            text="⚙️ Настройки",
            callback_data="settings"
        )
    )

    # Пятый ряд - информация
    keyboard.add(
        InlineKeyboardButton(
            text="❓ Помощь",
            callback_data="help"
        )
    )

    return keyboard


def create_settings_keyboard(user: User) -> InlineKeyboardMarkup:
    """
    Создаёт клавиатуру настроек профиля.

    Args:
        user: Объект пользователя для отображения текущих настроек.

    Returns:
        InlineKeyboardMarkup: Клавиатура настроек.
    """
    keyboard = InlineKeyboardMarkup(row_width=1)

    # Диагнозы
    diabetes_status = "✅" if user.has_diabetes else "❌"
    gout_status = "✅" if user.has_gout else "❌"
    celiac_status = "✅" if user.has_celiac else "❌"

    keyboard.add(
        InlineKeyboardButton(
            text=f"{diabetes_status} Сахарный диабет",
            callback_data="toggle_diabetes"
        ),
        InlineKeyboardButton(
            text=f"{gout_status} Подагра",
            callback_data="toggle_gout"
        ),
        InlineKeyboardButton(
            text=f"{celiac_status} Целиакия (глютен)",
            callback_data="toggle_celiac"
        )
    )

    # Кнопка возврата
    keyboard.add(
        InlineKeyboardButton(
            text="◀️ Назад в меню",
            callback_data="main_menu"
        )
    )

    return keyboard


def create_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт клавиатуру с кнопкой возврата в меню.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой "Назад".
    """
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            text="◀️ Главное меню",
            callback_data="main_menu"
        )
    )
    return keyboard


def create_category_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт клавиатуру выбора категории рецептов.

    Returns:
        InlineKeyboardMarkup: Клавиатура категорий.
    """
    keyboard = InlineKeyboardMarkup(row_width=2)

    keyboard.add(
        InlineKeyboardButton(text="🍳 Завтраки", callback_data="cat_breakfast"),
        InlineKeyboardButton(text="🍲 Основные", callback_data="cat_main")
    )
    keyboard.add(
        InlineKeyboardButton(text="🥗 Салаты", callback_data="cat_salad"),
        InlineKeyboardButton(text="🍜 Супы", callback_data="cat_soup")
    )
    keyboard.add(
        InlineKeyboardButton(text="🍰 Десерты", callback_data="cat_dessert"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")
    )

    return keyboard


# =============================================================================
# РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# =============================================================================

def register_handlers(bot: telebot.TeleBot) -> None:
    """
    Регистрирует все обработчики команд и сообщений.

    Вызывается при инициализации бота для подключения всех
    обработчиков к экземпляру бота.

    Args:
        bot: Экземпляр Telegram бота (pyTelegramBotAPI).

    Example:
        >>> bot = telebot.TeleBot(token)
        >>> register_handlers(bot)
        >>> bot.infinity_polling()
    """

    # =========================================================================
    # КОМАНДА /start - Приветствие и главное меню
    # =========================================================================

    @bot.message_handler(commands=["start"])
    def handle_start(message: Message) -> None:
        """
        Обработчик команды /start.

        Регистрирует нового пользователя или приветствует существующего.
        Отображает главное меню бота.

        Args:
            message: Объект сообщения Telegram.
        """
        db = SessionLocal()
        try:
            # Получаем или создаём пользователя
            user = get_or_create_user(
                db=db,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                language_code=message.from_user.language_code or "ru"
            )

            # Формируем приветственное сообщение
            welcome_text = (
                f"👋 <b>Добро пожаловать, {user.first_name or 'друг'}!</b>\n\n"
                f"🥗 <b>{settings.app_name}</b> — ваш персональный помощник "
                f"по питанию при подагре и диабете.\n\n"
                f"<b>Что умеет бот:</b>\n"
                f"• 🔍 Поиск рецептов средиземноморской диеты\n"
                f"• 🤖 AI-диетолог для консультаций\n"
                f"• 📍 Поиск магазинов и сравнение цен\n"
                f"• 📔 Ведение дневника питания\n"
                f"• 🛒 Список покупок с ценами\n\n"
                f"Выберите действие:"
            )

            bot.send_message(
                chat_id=message.chat.id,
                text=welcome_text,
                parse_mode="HTML",
                reply_markup=create_main_menu_keyboard()
            )

            logger.info(f"Пользователь {user.telegram_id} запустил бота")

        except Exception as exc:
            logger.error(f"Ошибка в /start: {exc}", exc_info=True)
            bot.send_message(
                chat_id=message.chat.id,
                text="❌ Произошла ошибка. Попробуйте позже."
            )
        finally:
            db.close()

    # =========================================================================
    # КОМАНДА /help - Справка
    # =========================================================================

    @bot.message_handler(commands=["help"])
    def handle_help(message: Message) -> None:
        """
        Обработчик команды /help.

        Отображает справочную информацию о боте и его функциях.

        Args:
            message: Объект сообщения Telegram.
        """
        help_text = (
            "<b>📚 Справка по {}</b>\n\n"
            "<b>Основные команды:</b>\n"
            "/start — Главное меню\n"
            "/help — Эта справка\n"
            "/settings — Настройки профиля\n"
            "/diary — Дневник питания\n"
            "/list — Список покупок\n\n"
            "<b>Функции бота:</b>\n\n"
            "🔍 <b>Поиск рецептов</b>\n"
            "Находит рецепты средиземноморской диеты, "
            "подходящие для вашего диагноза.\n\n"
            "🤖 <b>AI-диетолог</b>\n"
            "Отвечает на вопросы о питании на базе GPT-4.\n\n"
            "📍 <b>Магазины рядом</b>\n"
            "Показывает ближайшие магазины и сравнивает цены.\n\n"
            "📔 <b>Дневник питания</b>\n"
            "Отслеживание съеденного: калории, пурины, ГИ.\n\n"
            "🛒 <b>Список покупок</b>\n"
            "Добавляйте продукты и отмечайте купленные.\n\n"
            "<b>Поддержка:</b>\n"
            "📧 support@medmarket.bot"
        ).format(settings.app_name)

        bot.send_message(
            chat_id=message.chat.id,
            text=help_text,
            parse_mode="HTML",
            reply_markup=create_back_to_menu_keyboard()
        )

    # =========================================================================
    # КОМАНДА /settings - Настройки
    # =========================================================================

    @bot.message_handler(commands=["settings"])
    def handle_settings_command(message: Message) -> None:
        """
        Обработчик команды /settings.

        Args:
            message: Объект сообщения Telegram.
        """
        show_settings(bot, message.chat.id, message.from_user.id)

    # =========================================================================
    # ОБРАБОТЧИК CALLBACK КНОПОК
    # =========================================================================

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback(call: CallbackQuery) -> None:
        """
        Обработчик всех callback запросов от инлайн-кнопок.

        Маршрутизирует запросы к соответствующим функциям
        на основе callback_data.

        Args:
            call: Объект callback запроса.
        """
        try:
            # Отвечаем на callback, чтобы убрать "часики" на кнопке
            bot.answer_callback_query(call.id)

            user_id = call.from_user.id
            chat_id = call.message.chat.id
            data = call.data

            # Маршрутизация callback запросов
            if data == "main_menu":
                show_main_menu(bot, chat_id, user_id)

            elif data == "search_recipes":
                handle_search_recipes_start(bot, chat_id, user_id)

            elif data == "daily_recipe":
                handle_daily_recipe(bot, chat_id, user_id)

            elif data == "find_shops":
                handle_find_shops_start(bot, chat_id, user_id)

            elif data == "compare_prices":
                handle_compare_prices_start(bot, chat_id, user_id)

            elif data == "view_diary":
                handle_view_diary(bot, chat_id, user_id)

            elif data == "shopping_list":
                handle_shopping_list(bot, chat_id, user_id)

            elif data == "ask_dietician":
                handle_ask_dietician_start(bot, chat_id, user_id)

            elif data == "settings":
                show_settings(bot, chat_id, user_id)

            elif data == "help":
                handle_help(call.message)

            # Обработка категорий рецептов
            elif data.startswith("cat_"):
                category = data.replace("cat_", "")
                handle_category_recipes(bot, chat_id, user_id, category)

            # Переключение диагнозов
            elif data == "toggle_diabetes":
                toggle_diagnosis(bot, chat_id, user_id, "diabetes")

            elif data == "toggle_gout":
                toggle_diagnosis(bot, chat_id, user_id, "gout")

            elif data == "toggle_celiac":
                toggle_diagnosis(bot, chat_id, user_id, "celiac")

            else:
                logger.warning(f"Неизвестный callback: {data}")

        except Exception as exc:
            logger.error(f"Ошибка в callback {call.data}: {exc}", exc_info=True)
            bot.send_message(
                chat_id=call.message.chat.id,
                text="❌ Произошла ошибка. Попробуйте позже."
            )

    # =========================================================================
    # ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ
    # =========================================================================

    @bot.message_handler(content_types=["text"])
    def handle_text(message: Message) -> None:
        """
        Обработчик текстовых сообщений.

        Обрабатывает текст в зависимости от текущего состояния
        пользователя (FSM).

        Args:
            message: Объект сообщения Telegram.
        """
        user_id = message.from_user.id
        chat_id = message.chat.id
        text = message.text

        try:
            # Проверяем состояние пользователя
            if user_id in user_states:
                state = user_states[user_id].get("action")

                if state == "search_recipes":
                    process_recipe_search(bot, message)

                elif state == "ask_dietician":
                    process_dietician_question(bot, message)

                elif state == "compare_prices":
                    process_price_comparison(bot, message)

                elif state == "add_to_diary":
                    process_add_to_diary(bot, message)

                elif state == "add_to_shopping":
                    process_add_to_shopping(bot, message)

                else:
                    # Неизвестное состояние - показываем меню
                    del user_states[user_id]
                    show_main_menu(bot, chat_id, user_id)
            else:
                # Без состояния - показываем меню
                bot.send_message(
                    chat_id=chat_id,
                    text="👋 Используйте меню для навигации:",
                    reply_markup=create_main_menu_keyboard()
                )

        except Exception as exc:
            logger.error(f"Ошибка в обработке текста: {exc}", exc_info=True)
            bot.send_message(
                chat_id=chat_id,
                text="❌ Произошла ошибка. Попробуйте позже.",
                reply_markup=create_back_to_menu_keyboard()
            )

    # =========================================================================
    # ОБРАБОТЧИК ГЕОЛОКАЦИИ
    # =========================================================================

    @bot.message_handler(content_types=["location"])
    def handle_location(message: Message) -> None:
        """
        Обработчик сообщений с геолокацией.

        Используется для поиска ближайших магазинов.

        Args:
            message: Объект сообщения с геолокацией.
        """
        user_id = message.from_user.id
        chat_id = message.chat.id

        try:
            lat = message.location.latitude
            lon = message.location.longitude

            # Ищем ближайшие магазины
            shops = shop_service.find_nearby_shops(
                latitude=lat,
                longitude=lon,
                radius_km=2.0,
                limit=settings.max_shops_results
            )

            # Форматируем и отправляем результат
            text = shop_service.format_shops_for_display(shops)

            bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=create_back_to_menu_keyboard()
            )

            # Очищаем состояние
            if user_id in user_states:
                del user_states[user_id]

        except Exception as exc:
            logger.error(f"Ошибка обработки геолокации: {exc}", exc_info=True)
            bot.send_message(
                chat_id=chat_id,
                text="❌ Не удалось найти магазины. Попробуйте позже.",
                reply_markup=create_back_to_menu_keyboard()
            )

    logger.info("Все обработчики зарегистрированы")


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def show_main_menu(bot: telebot.TeleBot, chat_id: int, user_id: int) -> None:
    """
    Отображает главное меню.

    Args:
        bot: Экземпляр бота.
        chat_id: ID чата.
        user_id: ID пользователя.
    """
    # Очищаем состояние пользователя
    if user_id in user_states:
        del user_states[user_id]

    bot.send_message(
        chat_id=chat_id,
        text="<b>Главное меню</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=create_main_menu_keyboard()
    )


def show_settings(bot: telebot.TeleBot, chat_id: int, user_id: int) -> None:
    """
    Отображает настройки профиля.

    Args:
        bot: Экземпляр бота.
        chat_id: ID чата.
        user_id: ID пользователя.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()

        if not user:
            bot.send_message(chat_id, "❌ Пользователь не найден")
            return

        text = (
            "<b>⚙️ Настройки профиля</b>\n\n"
            "Укажите ваши диагнозы для фильтрации рецептов:\n\n"
            "✅ = учитывается при поиске\n"
            "❌ = не учитывается"
        )

        bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=create_settings_keyboard(user)
        )

    finally:
        db.close()


def toggle_diagnosis(
    bot: telebot.TeleBot,
    chat_id: int,
    user_id: int,
    diagnosis: str
) -> None:
    """
    Переключает статус диагноза пользователя.

    Args:
        bot: Экземпляр бота.
        chat_id: ID чата.
        user_id: ID пользователя.
        diagnosis: Тип диагноза (diabetes, gout, celiac).
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()

        if not user:
            return

        # Переключаем соответствующий диагноз
        if diagnosis == "diabetes":
            user.has_diabetes = not user.has_diabetes
        elif diagnosis == "gout":
            user.has_gout = not user.has_gout
        elif diagnosis == "celiac":
            user.has_celiac = not user.has_celiac

        db.commit()

        # Обновляем клавиатуру
        show_settings(bot, chat_id, user_id)

    finally:
        db.close()


def handle_search_recipes_start(
    bot: telebot.TeleBot,
    chat_id: int,
    user_id: int
) -> None:
    """
    Начинает процесс поиска рецептов.

    Args:
        bot: Экземпляр бота.
        chat_id: ID чата.
        user_id: ID пользователя.
    """
    user_states[user_id] = {"action": "search_recipes"}

    text = (
        "🔍 <b>Поиск рецептов</b>\n\n"
        "Введите название блюда или ингредиент:\n"
        "(например: 'курица', 'гречка', 'салат')"
    )

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("📂 По категориям", callback_data="show_categories")
    )
    keyboard.add(
        InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
    )

    bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


def process_recipe_search(bot: telebot.TeleBot, message: Message) -> None:
    """
    Обрабатывает поисковый запрос рецептов.

    Args:
        bot: Экземпляр бота.
        message: Сообщение с поисковым запросом.
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    query = message.text

    db = SessionLocal()
    try:
        # Получаем диагнозы пользователя
        user = db.query(User).filter(User.telegram_id == user_id).first()

        has_diabetes = user.has_diabetes if user else False
        has_gout = user.has_gout if user else False
        has_celiac = user.has_celiac if user else False

        # Ищем рецепты
        recipes = recipe_service.search_recipes(
            query=query,
            has_diabetes=has_diabetes,
            has_gout=has_gout,
            has_celiac=has_celiac,
            limit=settings.max_recipe_results
        )

        if recipes:
            text = f"✅ <b>Найдено рецептов: {len(recipes)}</b>\n\n"

            for i, recipe in enumerate(recipes, 1):
                text += (
                    f"<b>{i}. {recipe['name']}</b>\n"
                    f"   Калории: {recipe['calories']} ккал | "
                    f"ГИ: {recipe['glycemic_index']} | "
                    f"Пурины: {recipe['purines']} мг\n"
                    f"   ⏱ {recipe['cooking_time_min']} мин\n\n"
                )
        else:
            text = (
                f"❌ По запросу '{query}' рецепты не найдены.\n\n"
                "Попробуйте другой запрос или выберите категорию."
            )

        # Очищаем состояние
        del user_states[user_id]

        bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=create_back_to_menu_keyboard()
        )

    finally:
        db.close()


def handle_daily_recipe(
    bot: telebot.TeleBot,
    chat_id: int,
    user_id: int
) -> None:
    """
    Показывает рецепт дня.

    Args:
        bot: Экземпляр бота.
        chat_id: ID чата.
        user_id: ID пользователя.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()

        has_diabetes = user.has_diabetes if user else False
        has_gout = user.has_gout if user else False
        has_celiac = user.has_celiac if user else False

        recipe = recipe_service.get_random_recipe(
            has_diabetes=has_diabetes,
            has_gout=has_gout,
            has_celiac=has_celiac
        )

        if recipe:
            text = f"🍽 <b>Рецепт дня</b>\n\n"
            text += recipe_service.format_recipe_for_display(recipe)
        else:
            text = "❌ Не удалось подобрать рецепт для ваших диагнозов."

        bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=create_back_to_menu_keyboard()
        )

    finally:
        db.close()


def handle_category_recipes(
    bot: telebot.TeleBot,
    chat_id: int,
    user_id: int,
    category: str
) -> None:
    """
    Показывает рецепты по категории.

    Args:
        bot: Экземпляр бота.
        chat_id: ID чата.
        user_id: ID пользователя.
        category: Категория рецептов.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()

        recipes = recipe_service.get_recipes_by_category(
            category=category,
            has_diabetes=user.has_diabetes if user else False,
            has_gout=user.has_gout if user else False,
            has_celiac=user.has_celiac if user else False
        )

        category_names = {
            "breakfast": "🍳 Завтраки",
            "main": "🍲 Основные блюда",
            "salad": "🥗 Салаты",
            "soup": "🍜 Супы",
            "dessert": "🍰 Десерты"
        }

        cat_name = category_names.get(category, category)

        if recipes:
            text = f"<b>{cat_name}</b>\n\n"
            for i, r in enumerate(recipes, 1):
                text += f"{i}. {r['name']} ({r['calories']} ккал)\n"
        else:
            text = f"В категории '{cat_name}' нет подходящих рецептов."

        bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=create_back_to_menu_keyboard()
        )

    finally:
        db.close()


def handle_find_shops_start(
    bot: telebot.TeleBot,
    chat_id: int,
    user_id: int
) -> None:
    """
    Запрашивает геолокацию для поиска магазинов.

    Args:
        bot: Экземпляр бота.
        chat_id: ID чата.
        user_id: ID пользователя.
    """
    user_states[user_id] = {"action": "find_shops"}

    text = (
        "📍 <b>Поиск магазинов</b>\n\n"
        "Отправьте свою геолокацию для поиска ближайших магазинов.\n\n"
        "Нажмите кнопку 📎 → Геолокация"
    )

    bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="HTML",
        reply_markup=create_back_to_menu_keyboard()
    )


def handle_compare_prices_start(
    bot: telebot.TeleBot,
    chat_id: int,
    user_id: int
) -> None:
    """
    Начинает сравнение цен на продукт.

    Args:
        bot: Экземпляр бота.
        chat_id: ID чата.
        user_id: ID пользователя.
    """
    user_states[user_id] = {"action": "compare_prices"}

    text = (
        "💰 <b>Сравнение цен</b>\n\n"
        "Введите название продукта для сравнения цен:\n"
        "(например: 'гречка', 'оливковое масло', 'творог')"
    )

    bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="HTML",
        reply_markup=create_back_to_menu_keyboard()
    )


def process_price_comparison(bot: telebot.TeleBot, message: Message) -> None:
    """
    Обрабатывает запрос на сравнение цен.

    Args:
        bot: Экземпляр бота.
        message: Сообщение с названием продукта.
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    product_name = message.text

    comparison = shop_service.compare_prices(product_name)

    if comparison:
        text = shop_service.format_prices_for_display(comparison, product_name)
    else:
        text = f"❌ Цены на '{product_name}' не найдены."

    del user_states[user_id]

    bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="HTML",
        reply_markup=create_back_to_menu_keyboard()
    )


def handle_view_diary(
    bot: telebot.TeleBot,
    chat_id: int,
    user_id: int
) -> None:
    """
    Показывает дневник питания пользователя.

    Args:
        bot: Экземпляр бота.
        chat_id: ID чата.
        user_id: ID пользователя.
    """
    db = SessionLocal()
    try:
        entries = db.query(UserDiary).filter(
            UserDiary.user_id == user_id
        ).order_by(UserDiary.date_eaten.desc()).limit(10).all()

        if entries:
            text = "📔 <b>Дневник питания (последние 10)</b>\n\n"

            total_calories = 0
            total_purines = 0

            for entry in entries:
                date_str = entry.date_eaten.strftime("%d.%m %H:%M")
                text += (
                    f"<b>{entry.recipe_name}</b>\n"
                    f"   {date_str} | {entry.calories} ккал | "
                    f"ГИ: {entry.glycemic_index}\n\n"
                )
                total_calories += entry.calories
                total_purines += entry.purines

            text += (
                f"<b>Итого за период:</b>\n"
                f"Калории: {total_calories} ккал\n"
                f"Пурины: {total_purines:.1f} мг"
            )
        else:
            text = (
                "📔 <b>Дневник питания</b>\n\n"
                "Ваш дневник пока пуст.\n"
                "Начните добавлять рецепты!"
            )

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("➕ Добавить", callback_data="add_diary_entry")
        )
        keyboard.add(
            InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
        )

        bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    finally:
        db.close()


def handle_shopping_list(
    bot: telebot.TeleBot,
    chat_id: int,
    user_id: int
) -> None:
    """
    Показывает список покупок пользователя.

    Args:
        bot: Экземпляр бота.
        chat_id: ID чата.
        user_id: ID пользователя.
    """
    db = SessionLocal()
    try:
        items = db.query(ShoppingList).filter(
            ShoppingList.user_id == user_id,
            ShoppingList.is_purchased == False
        ).all()

        if items:
            text = "🛒 <b>Список покупок</b>\n\n"
            for item in items:
                text += f"• {item.product_name} ({item.quantity} {item.unit})\n"
        else:
            text = (
                "🛒 <b>Список покупок</b>\n\n"
                "Список пуст. Добавьте продукты!"
            )

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("➕ Добавить", callback_data="add_shopping_item")
        )
        keyboard.add(
            InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
        )

        bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    finally:
        db.close()


def handle_ask_dietician_start(
    bot: telebot.TeleBot,
    chat_id: int,
    user_id: int
) -> None:
    """
    Начинает диалог с AI-диетологом.

    Args:
        bot: Экземпляр бота.
        chat_id: ID чата.
        user_id: ID пользователя.
    """
    user_states[user_id] = {"action": "ask_dietician"}

    text = (
        "🤖 <b>AI-диетолог</b>\n\n"
        "Задайте любой вопрос о питании:\n"
        "(например: 'Что можно есть при подагре?')"
    )

    bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="HTML",
        reply_markup=create_back_to_menu_keyboard()
    )


def process_dietician_question(bot: telebot.TeleBot, message: Message) -> None:
    """
    Обрабатывает вопрос к AI-диетологу.

    Args:
        bot: Экземпляр бота.
        message: Сообщение с вопросом.
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    question = message.text

    # Отправляем сообщение о загрузке
    loading_msg = bot.send_message(
        chat_id=chat_id,
        text="🤔 Диетолог думает..."
    )

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()

        answer = gpt_service.ask_dietician(
            question=question,
            has_diabetes=user.has_diabetes if user else False,
            has_gout=user.has_gout if user else False,
            has_celiac=user.has_celiac if user else False
        )

        # Удаляем сообщение о загрузке
        bot.delete_message(chat_id, loading_msg.message_id)

        # Очищаем состояние
        del user_states[user_id]

        bot.send_message(
            chat_id=chat_id,
            text=f"🤖 <b>AI-диетолог:</b>\n\n{answer}",
            parse_mode="HTML",
            reply_markup=create_back_to_menu_keyboard()
        )

    except Exception as exc:
        logger.error(f"Ошибка AI-диетолога: {exc}", exc_info=True)
        bot.delete_message(chat_id, loading_msg.message_id)
        bot.send_message(
            chat_id=chat_id,
            text="❌ Диетолог временно недоступен. Попробуйте позже.",
            reply_markup=create_back_to_menu_keyboard()
        )
    finally:
        db.close()


def process_add_to_diary(bot: telebot.TeleBot, message: Message) -> None:
    """Заглушка для добавления в дневник."""
    bot.send_message(
        chat_id=message.chat.id,
        text="📔 Функция добавления в дневник в разработке.",
        reply_markup=create_back_to_menu_keyboard()
    )
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]


def process_add_to_shopping(bot: telebot.TeleBot, message: Message) -> None:
    """Заглушка для добавления в список покупок."""
    bot.send_message(
        chat_id=message.chat.id,
        text="🛒 Функция добавления в список в разработке.",
        reply_markup=create_back_to_menu_keyboard()
    )
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
