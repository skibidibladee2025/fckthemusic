# Dockerfile for MP3Juice API
# Deploy to: Railway, Render, Fly.io, Google Cloud Run, etc.

FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY sources/ ./sources/
COPY server.py .

# Expose port
EXPOSE 8000

# Run with gunicorn for production
CMD ["gunicorn", "server:app", "--workers", "2", "--bind", "0.0.0.0:8000", "--timeout", "120"]