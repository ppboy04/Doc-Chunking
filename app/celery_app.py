from celery import Celery
from app.config import REDIS_URL

celery_app = Celery(
    "book_chunk_processor",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    task_track_started=True,
    # each worker grabs one chunk at a time -> even distribution across workers
    worker_prefetch_multiplier=1,
)
