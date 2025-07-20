FROM python:3.11-slim

WORKDIR /app

COPY admin_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY admin_service/ .

ENV FLASK_APP=app
ENV FLASK_ENV=production

CMD ["flask", "run", "--host=0.0.0.0", "--port=5002"]