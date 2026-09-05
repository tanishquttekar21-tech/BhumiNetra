# Production Dockerfile for BhumiNetra Platform
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=10000

# Set working directory
WORKDIR /app

# Install system dependencies required by OpenCV and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies first for Docker caching layer
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose application port
EXPOSE 10000

# Start production application server using Gunicorn dynamically binding to PORT
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 wsgi:app

