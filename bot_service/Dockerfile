FROM python:3.11-slim

WORKDIR /app

COPY bot_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot_service/ /app/bot_service/

ENV PYTHONPATH=/app

CMD ["python", "-m", "bot_service.app"]