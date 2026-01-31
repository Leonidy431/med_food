"""
MedMarket Bot - Сервис AI-диетолога.

Этот модуль содержит сервис для взаимодействия с OpenAI GPT-4
как с AI-диетологом. Предоставляет персонализированные рекомендации
по питанию с учётом диагнозов пользователя.

Модуль соответствует стандартам PEP8 и PEP257.

Example:
    Использование сервиса::

        from services.gpt_service import GPTService

        gpt = GPTService()
        answer = gpt.ask_dietician(
            "Что можно есть при подагре?",
            has_gout=True
        )
        print(answer)

Author: MedMarket Team
License: MIT
Version: 1.0.0
"""

from typing import Optional

from loguru import logger

from config import settings

# Проверяем наличие OpenAI API
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI не установлен. GPT функции будут недоступны.")

# Проверяем наличие tenacity для retry логики
try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    logger.warning("Tenacity не установлен. Retry логика будет отключена.")


class GPTService:
    """
    Сервис AI-диетолога на базе OpenAI GPT-4.

    Предоставляет персонализированные рекомендации по питанию
    с учётом медицинских диагнозов пользователя (подагра, диабет, целиакия).

    Attributes:
        SYSTEM_PROMPT: Системное сообщение для настройки поведения GPT.
        MODEL_NAME: Название модели GPT для использования.
        MAX_TOKENS: Максимальное количество токенов в ответе.
        TEMPERATURE: Параметр креативности ответов (0-1).

    Example:
        >>> gpt = GPTService()
        >>> answer = gpt.ask_dietician("Можно ли есть помидоры при подагре?")
        >>> print(answer)
    """

    # Системное сообщение для GPT (контекст диетолога)
    SYSTEM_PROMPT = """Вы опытный врач-диетолог с 20-летним стажем работы.
Специализируетесь на средиземноморской диете для пациентов с:
- Подагрой (контроль пуринов, мочевой кислоты)
- Сахарным диабетом 2 типа (контроль гликемического индекса)
- Целиакией (безглютеновая диета)

Правила ответов:
1. Отвечайте кратко, по существу (2-4 абзаца максимум)
2. Используйте научно обоснованные рекомендации
3. Всегда предупреждайте о необходимости консультации с врачом
4. Отвечайте на русском языке
5. Не давайте медицинских диагнозов
6. Рекомендуйте продукты из списка 99 полезных продуктов средиземноморской диеты"""

    MODEL_NAME = "gpt-4"
    MAX_TOKENS = 500
    TEMPERATURE = 0.7

    def __init__(self) -> None:
        """
        Инициализирует сервис GPT.

        Настраивает API ключ OpenAI из переменных окружения.

        Raises:
            Warning: Если OPENAI_API_KEY не установлен.
        """
        if OPENAI_AVAILABLE and settings.openai_api_key:
            openai.api_key = settings.openai_api_key
            logger.info("GPT сервис инициализирован")
        else:
            logger.warning(
                "OpenAI API ключ не установлен. "
                "GPT функции будут использовать заглушки."
            )

    def ask_dietician(
        self,
        question: str,
        has_diabetes: bool = False,
        has_gout: bool = False,
        has_celiac: bool = False,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Получает рекомендацию от AI-диетолога.

        Формирует контекст на основе диагнозов пользователя
        и отправляет запрос к GPT-4.

        Args:
            question: Вопрос пользователя о питании.
            has_diabetes: Есть ли у пользователя диабет.
            has_gout: Есть ли у пользователя подагра.
            has_celiac: Есть ли у пользователя целиакия.
            max_tokens: Максимум токенов в ответе (опционально).

        Returns:
            str: Ответ от AI-диетолога.

        Example:
            >>> gpt = GPTService()
            >>> answer = gpt.ask_dietician(
            ...     "Какие крупы можно при диабете?",
            ...     has_diabetes=True
            ... )
        """
        # Проверяем доступность OpenAI
        if not OPENAI_AVAILABLE or not settings.openai_api_key:
            return self._get_fallback_response(question, has_gout, has_diabetes)

        try:
            # Формируем контекст диагнозов
            diagnosis_context = self._build_diagnosis_context(
                has_diabetes,
                has_gout,
                has_celiac
            )

            # Формируем полный промпт
            full_prompt = (
                f"{diagnosis_context}\n\n"
                f"Вопрос пользователя: {question}\n\n"
                f"Дайте рекомендацию с учётом диагнозов пользователя."
            )

            logger.info(f"GPT запрос: {question[:50]}...")

            # Отправляем запрос к GPT
            response = openai.ChatCompletion.create(
                model=self.MODEL_NAME,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=max_tokens or self.MAX_TOKENS,
                temperature=self.TEMPERATURE,
                top_p=0.9
            )

            # Извлекаем ответ
            answer = response.choices[0].message["content"].strip()
            logger.info(f"GPT ответ получен ({len(answer)} символов)")

            return answer

        except openai.APIError as exc:
            logger.error(f"Ошибка OpenAI API: {exc}")
            return self._get_error_response()

        except Exception as exc:
            logger.error(f"Неожиданная ошибка GPT: {exc}", exc_info=True)
            return self._get_error_response()

    def generate_meal_plan(
        self,
        days: int = 7,
        has_diabetes: bool = False,
        has_gout: bool = False,
        has_celiac: bool = False
    ) -> str:
        """
        Генерирует план питания на указанное количество дней.

        Args:
            days: Количество дней для плана (1-14).
            has_diabetes: Учитывать диабет.
            has_gout: Учитывать подагру.
            has_celiac: Учитывать целиакию.

        Returns:
            str: План питания в текстовом формате.

        Example:
            >>> gpt = GPTService()
            >>> plan = gpt.generate_meal_plan(days=3, has_gout=True)
            >>> print(plan)
        """
        if not OPENAI_AVAILABLE or not settings.openai_api_key:
            return self._get_fallback_meal_plan(days)

        try:
            # Ограничиваем количество дней
            days = min(max(1, days), 14)

            # Формируем диетические требования
            requirements = self._build_dietary_requirements(
                has_diabetes,
                has_gout,
                has_celiac
            )

            prompt = (
                f"Создайте план питания на {days} дней.\n"
                f"{requirements}\n\n"
                f"Для каждого дня укажите:\n"
                f"- Завтрак\n"
                f"- Обед\n"
                f"- Ужин\n"
                f"- Перекус\n\n"
                f"Используйте продукты из средиземноморской диеты. "
                f"Укажите примерную калорийность."
            )

            response = openai.ChatCompletion.create(
                model=self.MODEL_NAME,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )

            return response.choices[0].message["content"].strip()

        except Exception as exc:
            logger.error(f"Ошибка генерации плана: {exc}", exc_info=True)
            return self._get_fallback_meal_plan(days)

    def analyze_product(
        self,
        product_name: str,
        has_diabetes: bool = False,
        has_gout: bool = False,
        has_celiac: bool = False
    ) -> str:
        """
        Анализирует продукт на пригодность для диагнозов.

        Args:
            product_name: Название продукта для анализа.
            has_diabetes: Учитывать диабет.
            has_gout: Учитывать подагру.
            has_celiac: Учитывать целиакию.

        Returns:
            str: Анализ продукта с рекомендациями.

        Example:
            >>> gpt = GPTService()
            >>> analysis = gpt.analyze_product("говядина", has_gout=True)
        """
        if not OPENAI_AVAILABLE or not settings.openai_api_key:
            return f"Анализ продукта '{product_name}' временно недоступен."

        try:
            diagnosis_context = self._build_diagnosis_context(
                has_diabetes,
                has_gout,
                has_celiac
            )

            prompt = (
                f"{diagnosis_context}\n\n"
                f"Проанализируйте продукт: {product_name}\n\n"
                f"Укажите:\n"
                f"1. Можно ли употреблять при указанных диагнозах\n"
                f"2. Содержание пуринов (если важно для подагры)\n"
                f"3. Гликемический индекс (если важно для диабета)\n"
                f"4. Наличие глютена (если важно для целиакии)\n"
                f"5. Рекомендуемая порция и частота употребления"
            )

            response = openai.ChatCompletion.create(
                model=self.MODEL_NAME,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.MAX_TOKENS,
                temperature=0.5
            )

            return response.choices[0].message["content"].strip()

        except Exception as exc:
            logger.error(f"Ошибка анализа продукта: {exc}", exc_info=True)
            return f"Не удалось проанализировать продукт '{product_name}'."

    def _build_diagnosis_context(
        self,
        has_diabetes: bool,
        has_gout: bool,
        has_celiac: bool
    ) -> str:
        """
        Формирует контекст диагнозов для промпта.

        Args:
            has_diabetes: Диабет.
            has_gout: Подагра.
            has_celiac: Целиакия.

        Returns:
            str: Строка с контекстом диагнозов.
        """
        diagnoses = []

        if has_diabetes:
            diagnoses.append(
                "сахарный диабет 2 типа (нужны продукты с низким ГИ < 55)"
            )
        if has_gout:
            diagnoses.append(
                "подагра (нужны продукты с низким содержанием пуринов < 100мг/100г)"
            )
        if has_celiac:
            diagnoses.append(
                "целиакия (нужны безглютеновые продукты)"
            )

        if diagnoses:
            return f"Диагнозы пользователя: {', '.join(diagnoses)}."
        return "Пользователь без специальных диагнозов."

    def _build_dietary_requirements(
        self,
        has_diabetes: bool,
        has_gout: bool,
        has_celiac: bool
    ) -> str:
        """
        Формирует диетические требования для плана питания.

        Args:
            has_diabetes: Диабет.
            has_gout: Подагра.
            has_celiac: Целиакия.

        Returns:
            str: Строка с требованиями к диете.
        """
        requirements = []

        if has_diabetes:
            requirements.append("низкий гликемический индекс (ГИ < 55)")
        if has_gout:
            requirements.append("низкое содержание пуринов (< 100мг/100г)")
        if has_celiac:
            requirements.append("без глютена")

        if requirements:
            return f"Требования к диете: {', '.join(requirements)}."
        return "Сбалансированное питание средиземноморской диеты."

    def _get_fallback_response(
        self,
        question: str,
        has_gout: bool,
        has_diabetes: bool
    ) -> str:
        """
        Возвращает заглушку при недоступности GPT.

        Args:
            question: Вопрос пользователя.
            has_gout: Подагра.
            has_diabetes: Диабет.

        Returns:
            str: Заглушка ответа.
        """
        tips = []
        if has_gout:
            tips.append(
                "При подагре рекомендуется: овощи, фрукты, нежирные молочные "
                "продукты, цельнозерновые каши. Избегайте: красное мясо, "
                "субпродукты, алкоголь."
            )
        if has_diabetes:
            tips.append(
                "При диабете выбирайте продукты с низким ГИ: гречка, овсянка, "
                "бобовые, овощи. Избегайте: сахар, белый хлеб, сладости."
            )

        if not tips:
            tips.append(
                "Рекомендуем средиземноморскую диету: много овощей, фруктов, "
                "оливковое масло, рыба, орехи."
            )

        return (
            "AI-диетолог временно недоступен.\n\n"
            + "\n\n".join(tips) +
            "\n\nОбязательно проконсультируйтесь с врачом!"
        )

    def _get_fallback_meal_plan(self, days: int) -> str:
        """
        Возвращает простой план питания при недоступности GPT.

        Args:
            days: Количество дней.

        Returns:
            str: Простой план питания.
        """
        return (
            f"План питания на {days} дней (упрощённый):\n\n"
            "Завтрак: Овсянка с ягодами, зелёный чай\n"
            "Обед: Гречка с овощами, куриная грудка на пару\n"
            "Ужин: Рыба запечённая с брокколи\n"
            "Перекус: Йогурт натуральный, горсть орехов\n\n"
            "Для персонализированного плана настройте OPENAI_API_KEY."
        )

    def _get_error_response(self) -> str:
        """
        Возвращает сообщение об ошибке.

        Returns:
            str: Сообщение об ошибке.
        """
        return (
            "Извините, AI-диетолог временно недоступен.\n"
            "Пожалуйста, попробуйте позже или обратитесь к врачу."
        )
