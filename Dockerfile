# Multi-stage Dockerfile for Mealie MCP Server
# Uses uv for fast, reliable Python package management

# Stage 1: Builder - Install dependencies with uv
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies into the system Python
# --no-dev excludes development dependencies
RUN uv sync --no-dev --no-install-project

# Stage 2: Runtime - Minimal production image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    CONTAINER=true \
    PYTHONDONTWRITEBYTECODE=1

# Install uv in runtime for 'uv run' command
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create non-root user
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} appuser && \
    useradd -u ${UID} -g ${GID} -m -s /bin/bash appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy virtual environment and dependencies from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy pyproject.toml for uv run
COPY --chown=appuser:appuser pyproject.toml ./

# Copy application source code
COPY --chown=appuser:appuser src/ ./src/

# Switch to non-root user
USER appuser

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Health check - verify connection to Mealie API
# Runs every 30s, times out after 10s, starts checking after 5s, 3 retries before unhealthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; from src.mealie.client import MealieFetcher; MealieFetcher(os.getenv('MEALIE_BASE_URL'), os.getenv('MEALIE_API_KEY'))" || exit 1

# Runtime environment variables (must be provided at runtime)
# MEALIE_BASE_URL: URL of your Mealie instance (e.g., https://mealie.example.com)
# MEALIE_API_KEY: API key for Mealie authentication
# LOG_LEVEL: Optional logging level (default: INFO)

# Run the MCP server
CMD ["uv", "run", "src/server.py"]
