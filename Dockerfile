FROM python:3.11-slim

# ============================================================================
# MedMarket Bot - Dockerfile для Railway
# ============================================================================
# Production-ready контейнер для Telegram бота средиземноморской диеты.
#
# Build: docker build -t medmarket-bot .
# Run: docker run --env-file .env medmarket-bot
#
# Author: MedMarket Team
# Version: 1.0.0
# ============================================================================

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем переменные окружения Python
# PYTHONUNBUFFERED=1 - вывод логов в реальном времени
# PYTHONDONTWRITEBYTECODE=1 - не создаём .pyc файлы
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Копируем весь исходный код приложения
COPY . .

# Создаём директорию для логов
RUN mkdir -p /app/logs

# Health check - проверяем, запущен ли бот
# Проверяем наличие файла логов (признак работающего бота)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD test -f /app/logs/bot.log || exit 1

# Запускаем приложение
CMD ["python", "main.py"]
