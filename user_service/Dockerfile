FROM python:3.9-slim

WORKDIR /app

COPY user_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install pg_isready
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

# Copy the entire user_service directory into /app/user_service
COPY user_service/ /app/user_service/

ENV FLASK_ENV=production

COPY user_service/wait-for-postgres.sh .
RUN chmod +x wait-for-postgres.sh

# Update the command to run from the correct directory
CMD ["./wait-for-postgres.sh", "postgres", "5432", "python", "-m", "user_service.app"]