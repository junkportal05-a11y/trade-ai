# ======================================================================
# Multi-stage build for minimal production image (<200MB)
# ======================================================================
# Builder stage - installs dependencies into virtualenv
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install requirements (cached layer)
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# ======================================================================
# Runtime stage - minimal image with only runtime dependencies
# ======================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY backend/ /app/backend/
COPY backend/alembic/ /app/alembic/
COPY backend/alembic.ini /app/alembic.ini

# Create non-root user for security
RUN useradd --no-create-home --shell /bin/bash --uid 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Set Python path
ENV PYTHONPATH="/app/backend:${PYTHONPATH}"

# Use PORT env var (Cloud Run, HF Spaces, Docker Compose compatible)
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]