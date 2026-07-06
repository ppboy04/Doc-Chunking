## Summary
POC: split a large PDF (e.g. 500-page book) into 20-page chunks and
process them in parallel with Celery + Redis workers, writing results
to JSON (per-chunk + merged).

## What's included
- [ ] `app/chunker.py` — PDF splitter (20 pages/chunk, configurable)
- [ ] `app/tasks.py` — Celery tasks: extract text per chunk, merge all chunks
- [ ] `app/celery_app.py` — Celery + Redis wiring
- [ ] `app/main.py` — CLI orchestrator (split -> dispatch -> merge)
- [ ] `Dockerfile` + `docker-compose.yml` — redis, scalable workers, flower dashboard, app
- [ ] `README.md` — architecture + usage

## How to test locally
```bash
cp <your-500-page-book>.pdf input/book.pdf
docker compose up --build
# check output/book_full.json and output/results/*.json
# check http://localhost:5555 for live task progress (Flower)
```

## Open questions for reviewers
- Chunk size: fixed at 20 pages — should this be dynamic (by word count) instead?
- Processing logic in `process_chunk` is just text extraction — do we want
  summarization / embeddings / NER added here for v2?
- Worker replica count / autoscaling strategy for production
