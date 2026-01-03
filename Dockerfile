# Use official Python runtime as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
# WHY: postgresql-client for DB operations, build-essential for Python packages with C extensions
# WHY: curl for Docker healthchecks, libpq-dev for psycopg2 compilation
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project
COPY . /app/

# WHY: Create a non-root user for security (Celery security warning fix)
# Running as root is a security risk in production
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create directory for logs and set permissions
RUN mkdir -p /app/logs /app/staticfiles /app/media && \
    chown -R appuser:appuser /app

# Note: USER directive is set per-service in docker-compose.yml
# Web service runs as root (needs permissions for migrations)
# Celery services run as appuser (security best practice)

# Run migrations and collect static files on container start
# This is done in docker-compose command instead
