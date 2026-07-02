FROM python:3.10-slim
WORKDIR /app

# Copy and install requirements FIRST (Docker layer cache)
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Copy entire project
COPY . /app

# HuggingFace Spaces expects port 7860
EXPOSE 7860
ENV PYTHONPATH="/app/backend:${PYTHONPATH}"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]