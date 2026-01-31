"""
MedMarket Bot - Модуль базы данных.

Этот модуль содержит SQLAlchemy ORM модели и функции для работы
с базой данных PostgreSQL/SQLite. Поддерживает Railway PostgreSQL
и локальную SQLite для разработки.

Модуль соответствует стандартам PEP8 и PEP257.

Example:
    Использование сессии БД::

        from database import SessionLocal, User
        db = SessionLocal()
        user = db.query(User).filter(User.telegram_id == 123).first()
        db.close()

Attributes:
    Base: Базовый класс для всех ORM моделей.
    engine: SQLAlchemy engine для подключения к БД.
    SessionLocal: Factory для создания сессий БД.

Author: MedMarket Team
License: MIT
Version: 1.0.0
"""

from datetime import datetime
from typing import Generator, Optional

from loguru import logger
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

from config import settings


# =============================================================================
# ИНИЦИАЛИЗАЦИЯ SQLAlchemy
# =============================================================================

# Базовый класс для всех ORM моделей
Base = declarative_base()

# Создаём engine (подключение к БД)
# pool_pre_ping=True - проверяем соединение перед использованием
# echo=debug - логирование SQL запросов в режиме отладки
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,  # Базовый размер пула соединений
    max_overflow=20,  # Дополнительные соединения при пиковой нагрузке
)

# Factory для создания сессий БД
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# =============================================================================
# МОДЕЛЬ ПОЛЬЗОВАТЕЛЯ
# =============================================================================

class User(Base):
    """
    Модель пользователя Telegram.

    Хранит профиль пользователя, медицинские данные и настройки.
    Связана с дневником питания и списком покупок.

    Attributes:
        id: Уникальный идентификатор записи в БД.
        telegram_id: ID пользователя в Telegram (уникальный).
        username: Username пользователя в Telegram (@username).
        first_name: Имя пользователя.
        last_name: Фамилия пользователя.
        language_code: Код языка интерфейса (ru, en).
        is_active: Флаг активности пользователя.
        has_diabetes: Диагноз сахарный диабет.
        has_gout: Диагноз подагра.
        has_celiac: Диагноз целиакия (непереносимость глютена).
        weight_kg: Вес пользователя в кг.
        height_cm: Рост пользователя в см.
        age: Возраст пользователя.
        notification_enabled: Включены ли уведомления.
        created_at: Дата регистрации.
        updated_at: Дата последнего обновления профиля.

    Example:
        >>> user = User(telegram_id=123456, first_name="Иван")
        >>> db.add(user)
        >>> db.commit()
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), default="ru")

    # Флаг активности
    is_active = Column(Boolean, default=True)

    # Медицинские диагнозы
    has_diabetes = Column(Boolean, default=False)
    has_gout = Column(Boolean, default=False)
    has_celiac = Column(Boolean, default=False)

    # Физические параметры
    weight_kg = Column(Float, nullable=True)
    height_cm = Column(Float, nullable=True)
    age = Column(Integer, nullable=True)

    # Настройки уведомлений
    notification_enabled = Column(Boolean, default=True)

    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Связи с другими таблицами
    diary_entries = relationship(
        "UserDiary",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    shopping_items = relationship(
        "ShoppingList",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """Строковое представление пользователя."""
        return f"<User(telegram_id={self.telegram_id}, name={self.first_name})>"


# =============================================================================
# МОДЕЛЬ ДНЕВНИКА ПИТАНИЯ
# =============================================================================

class UserDiary(Base):
    """
    Модель дневника питания пользователя.

    Хранит записи о съеденных блюдах с пищевой ценностью
    и показателями, важными для диагнозов.

    Attributes:
        id: Уникальный идентификатор записи.
        user_id: ID пользователя (FK на users.telegram_id).
        recipe_id: ID рецепта из базы рецептов.
        recipe_name: Название рецепта/блюда.
        calories: Калорийность (ккал).
        proteins: Белки (г).
        fats: Жиры (г).
        carbs: Углеводы (г).
        glycemic_index: Гликемический индекс (для диабета).
        purines: Содержание пуринов мг/100г (для подагры).
        portion_g: Размер порции в граммах.
        meal_type: Тип приёма пищи (breakfast/lunch/dinner/snack).
        date_eaten: Дата и время приёма пищи.
        notes: Заметки пользователя.
        created_at: Дата создания записи.

    Example:
        >>> entry = UserDiary(
        ...     user_id=123456,
        ...     recipe_name="Гречка с овощами",
        ...     calories=280,
        ...     meal_type="lunch"
        ... )
    """

    __tablename__ = "user_diary"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    recipe_id = Column(String(100), nullable=True)
    recipe_name = Column(String(255), nullable=False)

    # Пищевая ценность
    calories = Column(Float, default=0.0)
    proteins = Column(Float, default=0.0)
    fats = Column(Float, default=0.0)
    carbs = Column(Float, default=0.0)

    # Показатели для диагнозов
    glycemic_index = Column(Integer, default=0)
    purines = Column(Float, default=0.0)
    portion_g = Column(Float, default=100.0)

    # Тип приёма пищи
    meal_type = Column(
        String(20),
        default="snack"
    )  # breakfast, lunch, dinner, snack

    # Время приёма пищи
    date_eaten = Column(DateTime, default=datetime.utcnow, index=True)

    # Заметки
    notes = Column(Text, nullable=True)

    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связь с пользователем
    user = relationship("User", back_populates="diary_entries")

    def __repr__(self) -> str:
        """Строковое представление записи дневника."""
        return f"<UserDiary(user={self.user_id}, meal={self.recipe_name})>"


# =============================================================================
# МОДЕЛЬ СПИСКА ПОКУПОК
# =============================================================================

class ShoppingList(Base):
    """
    Модель списка покупок пользователя.

    Хранит продукты, которые пользователь планирует купить,
    с возможностью отметки о покупке.

    Attributes:
        id: Уникальный идентификатор записи.
        user_id: ID пользователя (FK).
        product_name: Название продукта.
        quantity: Количество.
        unit: Единица измерения (г, кг, шт, л).
        is_purchased: Флаг покупки.
        marketplace_link: Ссылка на маркетплейс (Ozon/Яндекс.Маркет).
        price_estimate: Примерная цена.
        created_at: Дата добавления.
        purchased_at: Дата покупки.

    Example:
        >>> item = ShoppingList(
        ...     user_id=123456,
        ...     product_name="Брокколи",
        ...     quantity=500,
        ...     unit="г"
        ... )
    """

    __tablename__ = "shopping_list"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    product_name = Column(String(255), nullable=False)
    quantity = Column(Float, default=1.0)
    unit = Column(String(20), default="шт")  # г, кг, шт, л, мл
    is_purchased = Column(Boolean, default=False)
    marketplace_link = Column(String(500), nullable=True)
    price_estimate = Column(Float, nullable=True)

    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)
    purchased_at = Column(DateTime, nullable=True)

    # Связь с пользователем
    user = relationship("User", back_populates="shopping_items")

    def __repr__(self) -> str:
        """Строковое представление элемента списка."""
        return f"<ShoppingList(product={self.product_name}, qty={self.quantity})>"


# =============================================================================
# МОДЕЛЬ КЭША РЕЦЕПТОВ
# =============================================================================

class RecipeCache(Base):
    """
    Кэш рецептов для оптимизации производительности.

    Хранит предварительно загруженные рецепты с полной информацией
    о пищевой ценности и пригодности для различных диагнозов.

    Attributes:
        id: Уникальный идентификатор.
        recipe_id: Внешний ID рецепта.
        recipe_name: Название рецепта.
        description: Описание рецепта.
        ingredients: JSON с ингредиентами.
        instructions: JSON с инструкциями приготовления.
        calories: Калорийность на порцию.
        proteins: Белки на порцию.
        fats: Жиры на порцию.
        carbs: Углеводы на порцию.
        glycemic_index: Гликемический индекс.
        purines: Содержание пуринов.
        cooking_time_min: Время приготовления в минутах.
        servings: Количество порций.
        suitable_for_diabetes: Подходит для диабетиков.
        suitable_for_gout: Подходит при подагре.
        suitable_for_celiac: Подходит при целиакии (без глютена).
        category: Категория блюда (завтрак, обед, ужин, перекус).
        image_url: URL изображения рецепта.
        created_at: Дата добавления в кэш.

    Example:
        >>> recipe = RecipeCache(
        ...     recipe_id="r_001",
        ...     recipe_name="Овсянка с ягодами",
        ...     suitable_for_diabetes=True
        ... )
    """

    __tablename__ = "recipe_cache"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    recipe_id = Column(String(100), unique=True, index=True, nullable=False)
    recipe_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # JSON поля для гибкости структуры
    ingredients = Column(Text, nullable=True)  # JSON строка
    instructions = Column(Text, nullable=True)  # JSON строка

    # Пищевая ценность
    calories = Column(Float, default=0.0)
    proteins = Column(Float, default=0.0)
    fats = Column(Float, default=0.0)
    carbs = Column(Float, default=0.0)

    # Показатели для диагнозов
    glycemic_index = Column(Integer, default=0)
    purines = Column(Float, default=0.0)

    # Метаданные рецепта
    cooking_time_min = Column(Integer, default=30)
    servings = Column(Integer, default=2)

    # Флаги пригодности для диагнозов
    suitable_for_diabetes = Column(Boolean, default=False)
    suitable_for_gout = Column(Boolean, default=False)
    suitable_for_celiac = Column(Boolean, default=False)

    # Категория и изображение
    category = Column(String(50), default="main")  # breakfast, lunch, dinner, snack
    image_url = Column(String(500), nullable=True)

    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        """Строковое представление кэшированного рецепта."""
        return f"<RecipeCache(id={self.recipe_id}, name={self.recipe_name})>"


# =============================================================================
# МОДЕЛЬ ПРОДУКТОВ (99 ПРОДУКТОВ ИЗ ТЗ)
# =============================================================================

class Product(Base):
    """
    Модель продукта из базы 99 полезных продуктов.

    Содержит полную информацию о продукте с 12 параметрами
    для ранжирования и фильтрации по диагнозам.

    Attributes:
        id: Уникальный идентификатор.
        name: Название продукта.
        category: Категория (dairy, vegetables, berries, fruits, grains, nuts, fish).
        purines_mg: Содержание пуринов мг/100г.
        glycemic_index: Гликемический индекс (0-100).
        carbs_g: Углеводы г/100г.
        protein_g: Белки г/100г.
        fiber_g: Клетчатка г/100г.
        anti_inflammatory_score: Противовоспалительный индекс (0-10).
        vitamin_b_score: Оценка витаминов группы B (0-10).
        magnesium_mg: Магний мг/100г.
        potassium_mg: Калий мг/100г.
        antioxidants_orac: Антиоксиданты ORAC.
        availability_russia: Доступность в РФ (1-10).
        cost_rub_kg: Средняя цена руб/кг.
        preparation_difficulty: Сложность приготовления (1-5).
        description: Описание продукта.
        cooking_methods: JSON с методами приготовления.
        created_at: Дата добавления.

    Example:
        >>> product = Product(
        ...     name="Брокколи",
        ...     category="vegetables",
        ...     purines_mg=21.0,
        ...     glycemic_index=10
        ... )
    """

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    category = Column(String(50), index=True)  # dairy, vegetables, berries, etc.

    # 12 параметров для ранжирования
    purines_mg = Column(Float, default=0.0)  # мг/100г
    glycemic_index = Column(Integer, default=0)  # GI (0-100)
    carbs_g = Column(Float, default=0.0)  # г/100г
    protein_g = Column(Float, default=0.0)
    fiber_g = Column(Float, default=0.0)
    anti_inflammatory_score = Column(Float, default=5.0)  # 0-10
    vitamin_b_score = Column(Float, default=5.0)  # 0-10
    magnesium_mg = Column(Float, default=0.0)
    potassium_mg = Column(Float, default=0.0)
    antioxidants_orac = Column(Float, default=0.0)
    availability_russia = Column(Integer, default=5)  # 1-10
    cost_rub_kg = Column(Float, default=0.0)
    preparation_difficulty = Column(Integer, default=2)  # 1-5

    # Дополнительная информация
    description = Column(Text, nullable=True)
    cooking_methods = Column(Text, nullable=True)  # JSON список

    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        """Строковое представление продукта."""
        return f"<Product(name={self.name}, category={self.category})>"


# =============================================================================
# МОДЕЛЬ МАГАЗИНОВ
# =============================================================================

class Shop(Base):
    """
    Модель для хранения информации о магазинах.

    Кэширует данные о магазинах для быстрого поиска
    ближайших точек продаж.

    Attributes:
        id: Уникальный идентификатор.
        google_place_id: ID места в Google Maps.
        name: Название магазина.
        latitude: Широта.
        longitude: Долгота.
        address: Полный адрес.
        rating: Рейтинг магазина.
        working_hours: Часы работы.
        is_available: Доступен ли для поиска.
        created_at: Дата добавления.

    Example:
        >>> shop = Shop(
        ...     name="Пятёрочка",
        ...     latitude=55.7558,
        ...     longitude=37.6173,
        ...     address="Москва, ул. Тверская, 1"
        ... )
    """

    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    google_place_id = Column(String(255), unique=True, index=True, nullable=True)
    name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(500), nullable=True)
    rating = Column(Float, default=0.0)
    working_hours = Column(String(255), nullable=True)
    is_available = Column(Boolean, default=True)

    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        """Строковое представление магазина."""
        return f"<Shop(name={self.name}, address={self.address})>"


# =============================================================================
# ФУНКЦИИ ИНИЦИАЛИЗАЦИИ БАЗЫ ДАННЫХ
# =============================================================================

def init_db() -> None:
    """
    Инициализирует базу данных.

    Создаёт все таблицы, определённые в моделях, если они
    ещё не существуют. Безопасна для повторного вызова.

    Raises:
        Exception: При ошибке подключения к БД.

    Example:
        >>> init_db()
        >>> # Все таблицы созданы
    """
    try:
        logger.info("Создание таблиц в базе данных...")
        Base.metadata.create_all(bind=engine)
        logger.info("Таблицы успешно созданы")
    except Exception as exc:
        logger.error(f"Ошибка инициализации БД: {exc}", exc_info=True)
        raise


def get_db() -> Generator[Session, None, None]:
    """
    Генератор сессий базы данных.

    Используется как dependency injection в обработчиках.
    Автоматически закрывает сессию после использования.

    Yields:
        Session: Объект сессии SQLAlchemy.

    Example:
        >>> for db in get_db():
        ...     users = db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_by_telegram_id(
    db: Session,
    telegram_id: int
) -> Optional[User]:
    """
    Получает пользователя по Telegram ID.

    Args:
        db: Сессия БД.
        telegram_id: ID пользователя в Telegram.

    Returns:
        User: Объект пользователя или None если не найден.

    Example:
        >>> db = SessionLocal()
        >>> user = get_user_by_telegram_id(db, 123456)
        >>> if user:
        ...     print(user.first_name)
    """
    return db.query(User).filter(User.telegram_id == telegram_id).first()


def create_user(
    db: Session,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    language_code: str = "ru"
) -> User:
    """
    Создаёт нового пользователя в БД.

    Args:
        db: Сессия БД.
        telegram_id: ID пользователя в Telegram.
        username: Username пользователя.
        first_name: Имя пользователя.
        last_name: Фамилия пользователя.
        language_code: Код языка.

    Returns:
        User: Созданный объект пользователя.

    Example:
        >>> db = SessionLocal()
        >>> user = create_user(db, 123456, first_name="Иван")
        >>> print(user.id)
    """
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        language_code=language_code
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"Создан новый пользователь: {telegram_id}")
    return user


def get_or_create_user(
    db: Session,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    language_code: str = "ru"
) -> User:
    """
    Получает существующего или создаёт нового пользователя.

    Args:
        db: Сессия БД.
        telegram_id: ID пользователя в Telegram.
        username: Username пользователя.
        first_name: Имя пользователя.
        last_name: Фамилия пользователя.
        language_code: Код языка.

    Returns:
        User: Объект пользователя (существующий или созданный).

    Example:
        >>> db = SessionLocal()
        >>> user = get_or_create_user(db, 123456, first_name="Иван")
    """
    user = get_user_by_telegram_id(db, telegram_id)
    if user:
        return user
    return create_user(
        db,
        telegram_id,
        username,
        first_name,
        last_name,
        language_code
    )
