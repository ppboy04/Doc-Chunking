FROM python:3.11-slim

WORKDIR /srv

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN mkdir -p /data/input /data/output

ENV PYTHONUNBUFFERED=1 \
    INPUT_DIR=/data/input \
    OUTPUT_DIR=/data/output \
    REDIS_URL=redis://redis:6379/0

# Default command is overridden per-service in docker-compose.yml
CMD ["python", "-m", "app.main", "/data/input/book.pdf"]
