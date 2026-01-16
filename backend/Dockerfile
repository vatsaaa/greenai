# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# 1. Install System Dependencies
# libpq-dev and gcc are required to build psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python Dependencies
# We copy ONLY the requirements file first. 
# This leverages Docker cache: if requirements.txt hasn't changed, this step is skipped.
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.lock.txt

# 3. Copy Source Code
# We copy the backend code and the tools folder (for data generation)
COPY backend/ ./backend/
COPY tools/ ./tools/

# Create a non-root user for safety
RUN groupadd --system appgroup && useradd --system --gid appgroup --create-home appuser
RUN chown -R appuser:appgroup /app

# Default command (overridden by docker-compose)
USER appuser
CMD ["python", "--version"]