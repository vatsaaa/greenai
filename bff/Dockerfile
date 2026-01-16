# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# 1. Install System Dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python Dependencies
# Copy both lock and plain requirements so the image can build even when
# `requirements.lock.txt` is not present (fallback to `requirements.txt`).
COPY requirements.lock.txt requirements.txt ./
RUN if [ -f requirements.lock.txt ]; then \
            pip install --no-cache-dir --only-binary=:all: -r requirements.lock.txt; \
        else \
            pip install --no-cache-dir -r requirements.txt; \
        fi
RUN pip install --no-cache-dir gunicorn

# 3. Copy Source Code
COPY bff/ ./bff/

# Expose the API port
EXPOSE 8000

# Command to run the application
RUN groupadd --system appgroup && useradd --system --gid appgroup --create-home appuser
RUN chown -R appuser:appgroup /app

USER appuser
CMD ["gunicorn", "-c", "bff/gunicorn_conf.py", "bff.main:app"]