# Use Python 3.10 slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager via pip
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY pipeline.py ./
COPY app.py ./
COPY templates/ ./templates/

# Install Python dependencies using UV
RUN uv sync --frozen

# Create data directory
RUN mkdir -p /app/data/uploads /app/data/results

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Run the application
CMD ["uv", "run", "python", "app.py"]
