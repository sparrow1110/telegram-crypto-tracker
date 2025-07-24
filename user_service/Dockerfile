FROM python:3.11-slim

WORKDIR /app

COPY user_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

COPY user_service/ /app/user_service/

ENV PYTHONPATH=/app

COPY user_service/wait-for-postgres.sh .
RUN chmod +x wait-for-postgres.sh

CMD ["./wait-for-postgres.sh", "postgres", "5432", "uvicorn", "user_service.app:app", "--host", "0.0.0.0", "--port", "5001"]