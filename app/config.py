import os

# Number of pages per chunk (per your ask: 20 pages per chunk)
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "20"))

# Where the source PDF lives inside the container
INPUT_DIR = os.getenv("INPUT_DIR", "/data/input")

# Where chunk PDFs + result JSON files are written
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/data/output")

# Celery broker / result backend (Redis, started by docker-compose)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
