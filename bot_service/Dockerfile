FROM python:3.9-slim

WORKDIR /app

COPY bot_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot_service/ .

CMD ["python", "app.py"]