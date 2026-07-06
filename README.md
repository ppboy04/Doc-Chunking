# Book Chunk Processor (POC)

Splits a large PDF (e.g. a ~500-page book) into fixed-size page chunks
(default **20 pages**), processes each chunk **in parallel** using
**Celery workers backed by Redis**, and writes the extracted content to
JSON — one file per chunk, plus one merged file for the whole book.

## Architecture

```
                 ┌─────────────┐
   book.pdf ───► │  chunker.py │  splits into 20-page PDFs
                 └──────┬──────┘
                        │  chunk_0000.pdf ... chunk_00NN.pdf
                        ▼
                 ┌─────────────────────┐
                 │   Celery "chord"    │  fans chunks out to N workers
                 └──────────┬──────────┘
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
        worker #1      worker #2      worker #3   (docker-compose replicas)
             │              │              │
             │   each worker, per page:    │
             │   1. extract text (pdfplumber)
             │   2. embed text (sentence-transformers)
             │   3. INSERT INTO page_chunks (text, embedding) -- Postgres/pgvector
             │              │              │
             ▼              ▼              ▼
     output/results/chunk_0000.json, chunk_0001.json, ...
                        │
                        ▼
              merge_results (Celery task)
                        │
                        ▼
              output/book_full.json   (final combined result)
```

- **Redis** is the message broker + result backend for Celery.
- **Postgres + pgvector** stores every page's text alongside its
  embedding vector, so you can run semantic search over the whole
  book once processing finishes (see below).
- **Workers** are horizontally scalable — bump `deploy.replicas` in
  `docker-compose.yml`, or run `docker compose up --scale worker=8`.
- **Flower** (http://localhost:5555) gives you a live dashboard of task
  progress, retries, and throughput.
- Each chunk task extracts text with `pdfplumber`, embeds + stores it
  in Postgres, and writes its own JSON immediately, so partial results
  are available even before the whole book finishes.

## Postgres / pgvector

`app/db.py` defines one table, `page_chunks`:

| column        | type         | notes                              |
|---------------|--------------|-------------------------------------|
| `id`          | serial PK    |                                      |
| `source_file` | text, indexed| which book this page came from       |
| `chunk_id`    | int          | which 20-page chunk it belongs to    |
| `page_number` | int          |                                      |
| `word_count`  | int          |                                      |
| `text`        | text         | full page text                       |
| `embedding`   | `vector(384)`| pgvector column, cosine search       |

`docker-compose.yml` uses the official `pgvector/pgvector:pg16` image,
so the extension is already compiled in — `init_db()` just runs
`CREATE EXTENSION IF NOT EXISTS vector` and creates the table.

Embeddings are generated locally with `sentence-transformers`
(`all-MiniLM-L6-v2`, 384-dim, no API key required — first run downloads
the model, then it's cached in the `hf_cache` volume). To use a hosted
embedding API instead (OpenAI, Anthropic, Cohere, etc.), swap the body
of `embed()` in `app/embeddings.py` and update `EMBEDDING_DIM` in
`app/config.py` to match its output size.

### Run a semantic search once the book is processed

```bash
docker compose run --rm app python -m app.search "what causes bitcoin price volatility"
```

or locally:
```bash
python search_vectors.py "regulatory risk" --top-k 3
```

This embeds your query and returns the closest pages by cosine
distance — the basic building block for RAG over the book.

## 🔍 Vector Search Features

All PDF pages are automatically embedded and stored in PostgreSQL with pgvector,
enabling semantic search over extracted content.

### Semantic Search
```bash
# Search for semantically similar content
python search_vectors.py "quantum computing"

# Get top 10 results
python search_vectors.py "machine learning applications" --top-k 10

# Filter by source file
python search_vectors.py "natural language" --source book.pdf
```

### Keyword Search
```bash
# Find pages containing specific keywords
python search_vectors.py --keywords "regulation" "compliance" "audit"
```

### Database Management
```bash
# List all documents in database
python search_vectors.py --list-documents

# Show database statistics
python search_vectors.py --stats
```

### Using Embeddings Programmatically
```python
from app.db import SessionLocal, similarity_search
from app.embeddings import embed

query = "algorithmic trading"
query_embedding = embed(query)

db = SessionLocal()
results = similarity_search(db, query_embedding, top_k=5)

for result in results:
    print(f"Page {result.page_number}: {result.text[:100]}...")
db.close()
```

**Embedding Model**: `all-MiniLM-L6-v2` (384-dimensional)  
**Search Algorithm**: Cosine distance via pgvector `<=>` operator  
**Database**: PostgreSQL 16 + pgvector extension

## Project layout

```
book-chunk-processor/
├── app/
│   ├── chunker.py       # splits PDF into N-page chunk PDFs
│   ├── tasks.py         # Celery tasks: process_chunk, merge_results
│   ├── celery_app.py    # Celery app + Redis config
│   ├── db.py            # Postgres + pgvector models, init, similarity search
│   ├── embeddings.py    # local sentence-transformers embedding generation
│   ├── search.py        # CLI: semantic search over stored embeddings
│   ├── config.py        # env-driven settings (CHUNK_SIZE, DB, embeddings, etc)
│   └── main.py          # CLI orchestrator (split -> dispatch -> merge)
├── input/                # put your source PDF here
├── output/                # chunk PDFs + JSON results land here
├── Dockerfile
├── docker-compose.yml    # redis, postgres+pgvector, workers, flower, app
└── requirements.txt
```

## Running it

### 1. Docker (recommended)

```bash
cp your-book.pdf input/book.pdf
docker compose up --build
```

This starts Redis, 3 worker replicas, Flower, and the orchestrator app
(which runs once and exits after processing `input/book.pdf`).

Scale workers up/down on the fly:
```bash
docker compose up --scale worker=8 -d
```

### 2. Local (no Docker) — for quick dev/testing

```bash
pip install -r requirements.txt
redis-server &                                  # needs redis installed locally
celery -A app.celery_app.celery_app worker --loglevel=info &
python -m app.main input/book.pdf
```

## Output

- `output/manifest.json` — list of chunks (page ranges, chunk paths)
- `output/results/chunk_XXXX.json` — per-chunk extracted text + stats
- `output/book_full.json` — final merged JSON for the entire book

Each chunk JSON looks like:
```json
{
  "chunk_id": 0,
  "start_page": 1,
  "end_page": 20,
  "word_count": 5321,
  "pages": [
    {"page_number": 1, "word_count": 260, "text": "..."},
    ...
  ]
}
```

## Configuration

Environment variables (see `app/config.py`):

| Variable      | Default                 | Purpose                          |
|---------------|--------------------------|-----------------------------------|
| `CHUNK_SIZE`  | `20`                     | pages per chunk                   |
| `INPUT_DIR`   | `/data/input`            | source PDF location                |
| `OUTPUT_DIR`  | `/data/output`           | where results are written          |
| `REDIS_URL`   | `redis://redis:6379/0`  | Celery broker/backend              |
| `DATABASE_URL`| `postgresql+psycopg2://postgres:postgres@postgres:5432/bookdb` | Postgres/pgvector connection |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2`  | sentence-transformers model name   |
| `EMBEDDING_DIM`   | `384`                | must match the model's output size |

## Notes / next steps for this POC

- Text extraction is intentionally simple (`pdfplumber`) — swap in
  OCR, LLM summarization, embeddings, etc. inside `process_chunk` in
  `app/tasks.py` without touching the orchestration logic.
- Retries: each chunk task retries up to 2x on failure (transient
  I/O errors, etc.) before failing the whole chord.
- For very large books, consider chunking by token/word count instead
  of fixed page count if pages are uneven in density.
