# Stage 1: Base image with dependencies
FROM python:3.12-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration and source code for proper package discovery
COPY pyproject.toml ./
COPY src ./src
COPY dashboard ./dashboard

# Install packages (both src and dashboard now exist)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -e ".[dev]"

# Stage 2: Development image
FROM base as development

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose ports
EXPOSE 8000 8501

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
