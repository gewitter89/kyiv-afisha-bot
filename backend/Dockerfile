FROM python:3.11-slim

WORKDIR /workspace

# Install system dependencies needed for compiling psycopg2 or other tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend files
COPY . .

# Set python path
ENV PYTHONPATH=/workspace

EXPOSE 8000

# Script to run migrations, seed data, and start server
CMD sh -c "alembic upgrade head && python app/db_seed.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"
