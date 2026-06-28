FROM python:3.11-slim

# System deps for pandas/numpy compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Non-root user (Hugging Face requires UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy requirements first for layer caching
COPY --chown=user backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy entire backend with new app/ structure
COPY --chown=user backend/ .

# Ensure old modules remain importable by adding root to path
ENV PYTHONPATH="/home/user/app:${PYTHONPATH}"

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
