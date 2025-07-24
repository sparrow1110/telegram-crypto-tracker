FROM python:3.11-slim

WORKDIR /app

COPY admin_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY admin_service/ /app/admin_service/

ENV PYTHONPATH=/app

CMD ["uvicorn", "admin_service.app:app", "--host", "0.0.0.0", "--port", "5002"]