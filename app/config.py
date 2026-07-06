import os

# Number of pages per chunk (per your ask: 20 pages per chunk)
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "2"))

# Where the source PDF lives inside the container
INPUT_DIR = os.getenv("INPUT_DIR", "/data/input")

# Where chunk PDFs + result JSON files are written
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/data/output")

# Celery broker / result backend (Redis, started by docker-compose)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Postgres + pgvector
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@postgres:5432/bookdb",
)

# Embedding model + its output dimension (must match the vector column size)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))  # 384 for all-MiniLM-L6-v2
