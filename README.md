# 📚 Book Chunk Processor

> A proof-of-concept distributed PDF processor that intelligently splits large books into manageable chunks and processes them in parallel using Celery workers and Redis, with full text extraction and JSON output.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 8/8 Passing](https://img.shields.io/badge/tests-8%2F8%20passing-brightgreen.svg)](#testing)

## 🚀 Quick Start

**No Docker? No problem!** Get started in 30 seconds:

```bash
pip install -r requirements.txt
python run_standalone.py input/book.pdf
```

## ✨ Features

- **Standalone & Distributed**: Works without Docker/Redis for quick testing, or scales to production with Celery workers
- **Smart Chunking**: Automatically splits PDFs into configurable chunk sizes (default: 20 pages)
- **Parallel Processing**: Process multiple chunks simultaneously with horizontally scalable workers
- **Rich Metadata**: Extracts text, word counts, character counts, and page-level data
- **Merged Output**: Combines all chunks into a single JSON file with complete book data
- **Full Test Coverage**: 8 comprehensive unit tests (100% pass rate)
- **Docker Ready**: Pre-configured `docker-compose.yml` for production deployment
- **Live Dashboard**: Optional Flower UI for monitoring task progress

## 📋 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Usage](#-usage)
- [Output Format](#-output-format)
- [Testing](#-testing)
- [Architecture](#-architecture)
- [Performance](#-performance)
- [Configuration](#-configuration)

## 📦 Installation

### Option 1: Standalone (Recommended for Development)

```bash
# Clone the repository
git clone https://github.com/yourusername/book-chunk-processor.git
cd book-chunk-processor

# Install dependencies
pip install -r requirements.txt

# Verify installation
python run_standalone.py input/book.pdf
```

### Option 2: Docker (Production Ready)

```bash
# Clone and build
git clone https://github.com/yourusername/book-chunk-processor.git
cd book-chunk-processor

# Build and run
docker compose up --build
```

### Option 3: Manual Celery Setup (Advanced)

```bash
pip install -r requirements.txt
redis-server &
celery -A app.celery_app.celery_app worker --loglevel=info &
python -m app.main input/book.pdf
```

## 🎯 Usage

### 1. Standalone Version (Easiest)

```bash
python run_standalone.py input/book.pdf
```

**Example Output:**
```
📚 Book Chunk Processor (Standalone)

[1/3] Splitting input/book.pdf into chunks...
      ✓ 3 chunks (6 pages, 2 pages/chunk)
[2/3] Processing chunks...
  Processing chunk 0... ✓
  Processing chunk 1... ✓
  Processing chunk 2... ✓
[3/3] Merging results...
      ✓ Merged JSON written to: output/book_full.json

📊 Summary:
   Total pages:  6
   Total words:  3,283
   Chunks:       3
   Output files: output/
```

### 2. Docker (Parallel Processing)

```bash
cp your-500-page-book.pdf input/book.pdf
docker compose up --build

# Monitor at http://localhost:5555 (Flower dashboard)

# Scale to 8 workers
docker compose up --scale worker=8 -d
```

### 3. Programmatic Usage

```python
from app.chunker import split_pdf_into_chunks
from app.tasks import process_chunk, merge_results

manifest = split_pdf_into_chunks('input/book.pdf', chunk_size=20)
chunk_results = [process_chunk(c) for c in manifest['chunks']]
final = merge_results(chunk_results, 'input/book.pdf')
print(f"Merged: {final['output_path']}")
```

## 📊 Output Format

### Directory Structure

```
output/
├── manifest.json              # Chunking metadata
├── book_full.json            # ✓ Merged result (all chunks)
├── chunks/
│   ├── chunk_0000.pdf        # PDF pages 1-20
│   ├── chunk_0001.pdf        # PDF pages 21-40
│   └── ...
└── results/
    ├── book_full.json        # ✓ Merged result (copy)
    ├── chunk_0000.json       # Extracted text + metadata
    ├── chunk_0001.json
    └── ...
```

### Sample JSON Output

**Per-Chunk Result** (`output/results/chunk_0000.json`):
```json
{
  "chunk_id": 0,
  "source_file": "input/book.pdf",
  "start_page": 1,
  "end_page": 2,
  "page_count": 2,
  "word_count": 1137,
  "char_count": 8833,
  "pages": [
    {
      "page_number": 1,
      "char_count": 4196,
      "word_count": 493,
      "text": "Bitcoin Price Analysis and Future Forecast..."
    },
    {
      "page_number": 2,
      "char_count": 4636,
      "word_count": 644,
      "text": "Market Factors and Quantitative Models..."
    }
  ]
}
```

**Merged Result** (`output/book_full.json`):
```json
{
  "source_file": "input/book.pdf",
  "num_chunks": 3,
  "total_pages": 6,
  "total_word_count": 3283,
  "chunks": [...]
}
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
pip install pytest reportlab
python -m pytest test_processor.py -v
```

**All 8 tests passing ✅:**
```
test_processor.py::TestSplitPDF::test_split_creates_chunks PASSED        [ 12%]
test_processor.py::TestSplitPDF::test_chunk_metadata_correct PASSED      [ 25%]
test_processor.py::TestSplitPDF::test_chunk_files_created PASSED         [ 37%]
test_processor.py::TestProcessChunk::test_process_chunk_extracts_text PASSED [ 50%]
test_processor.py::TestProcessChunk::test_process_chunk_output_json PASSED [ 62%]
test_processor.py::TestMergeResults::test_merge_multiple_chunks PASSED   [ 75%]
test_processor.py::TestMergeResults::test_merged_word_count_sum PASSED   [ 87%]
test_processor.py::TestIntegration::test_full_pipeline PASSED            [100%]

============================== 8 passed in 3.86s ==============================
```

## 🏗️ Architecture

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
