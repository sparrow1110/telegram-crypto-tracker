FROM python:3.11-slim

WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости
COPY crypto_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем всю директорию crypto_service в /app/crypto_service
COPY crypto_service/ /app/crypto_service/

# Устанавливаем PYTHONPATH, чтобы Python находил модуль
ENV PYTHONPATH=/app

# Запускаем Uvicorn с правильным путём к модулю
CMD ["uvicorn", "crypto_service.app:app", "--host", "0.0.0.0", "--port", "5003"]