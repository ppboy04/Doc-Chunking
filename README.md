# Book Chunk Processor (POC)

Splits a large PDF (e.g. a ~500-page book) into fixed-size page chunks
(default **20 pages**), processes each chunk **in parallel** using
**Celery workers backed by Redis**, and writes the extracted content to
JSON — one file per chunk, plus one merged file for the whole book.

**Quick Start:** Use `run_standalone.py` for instant testing without Docker/Redis:
```bash
python run_standalone.py input/book.pdf
```

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
- **Workers** are horizontally scalable — bump `deploy.replicas` in
  `docker-compose.yml`, or run `docker compose up --scale worker=8`.
- **Flower** (http://localhost:5555) gives you a live dashboard of task
  progress, retries, and throughput.
- Each chunk task extracts text with `pdfplumber` and writes its own
  JSON immediately, so partial results are available even before the
  whole book finishes.

## Project layout

```
book-chunk-processor/
├── app/
│   ├── chunker.py       # splits PDF into N-page chunk PDFs
│   ├── tasks.py         # Celery tasks: process_chunk, merge_results
│   ├── celery_app.py    # Celery app + Redis config
│   ├── config.py        # env-driven settings (CHUNK_SIZE, paths, etc)
│   └── main.py          # CLI orchestrator (split -> dispatch -> merge)
├── run_standalone.py    # ✓ NEW: Standalone version (no Docker needed)
├── test_processor.py    # ✓ NEW: Comprehensive test suite (8 tests)
├── show_results.py      # Utility to display processing results
├── process_small_chunks.py # Example script for custom chunk sizes
├── input/               # put your source PDF here
├── output/              # ✓ chunk PDFs + JSON results (merged result included)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt

```

## Running it

### 1. Standalone (Recommended for quick testing - No Docker required!)

```bash
pip install -r requirements.txt
python run_standalone.py input/book.pdf
```

This is the **easiest way to get started**. It processes your PDF synchronously (one chunk at a time) and generates the same output as the full parallel version. Perfect for development and testing.

**Actual Example Output:**
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

You can customize chunk size:
```bash
python -c "from run_standalone import split_pdf_into_chunks, process_chunk, merge_results; ..."
# Change chunk_size parameter to split differently (default: 20 pages)
```

### 2. Docker (for parallel processing & production)

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

### 3. Local with Celery (no Docker) — for dev/testing

```bash
pip install -r requirements.txt
redis-server &                                  # needs redis installed locally
celery -A app.celery_app.celery_app worker --loglevel=info &
python -m app.main input/book.pdf
```

## Output

After processing, you'll find:

```
output/
├── manifest.json                    # chunk metadata (page ranges, paths)
├── book_full.json                   # ✓ merged result (all chunks combined)
├── chunks/
│   ├── chunk_0000.pdf              # pages 1-2
│   ├── chunk_0001.pdf              # pages 3-4
│   └── chunk_0002.pdf              # pages 5-6
└── results/
    ├── book_full.json              # ✓ merged result (copy for convenience)
    ├── chunk_0000.json             # extracted text + metadata for pages 1-2
    ├── chunk_0001.json             # extracted text + metadata for pages 3-4
    └── chunk_0002.json             # extracted text + metadata for pages 5-6
```

**Example from processing a 6-page book:**

- `output/manifest.json` — list of 3 chunks with page ranges
- `output/results/chunk_0000.json` — pages 1-2, 1,137 words extracted
- `output/results/chunk_0001.json` — pages 3-4, 1,337 words extracted
- `output/results/chunk_0002.json` — pages 5-6, 809 words extracted
- `output/book_full.json` — **all 3 chunks merged, 3,283 total words**

Each chunk JSON contains:
```json
{
  "chunk_id": 0,
  "start_page": 1,
  "end_page": 2,
  "page_count": 2,
  "word_count": 1137,
  "char_count": 8833,
  "pages": [
    {
      "page_number": 1,
      "word_count": 493,
      "char_count": 4196,
      "text": "Bitcoin Price Analysis and Future Forecast: A Study Based on..."
    },
    {
      "page_number": 2,
      "word_count": 644,
      "char_count": 4636,
      "text": "ICDSE2025-TheInternationalConferenceonDataScienceandEngineering..."
    }
  ]
}
```
  ]
}
```

## Testing

Run the comprehensive test suite (8 tests covering the entire pipeline):

```bash
pip install pytest reportlab
python -m pytest test_processor.py -v
```

**Test Results:**
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

All tests verify correct PDF splitting, text extraction, and result merging.

## Configuration

Environment variables (see `app/config.py`):

| Variable      | Default                 | Purpose                          |
|---------------|--------------------------|-----------------------------------|
| `CHUNK_SIZE`  | `20`                     | pages per chunk                   |
| `INPUT_DIR`   | `/data/input`            | source PDF location                |
| `OUTPUT_DIR`  | `/data/output`           | where results are written          |
| `REDIS_URL`   | `redis://redis:6379/0`  | Celery broker/backend              |

## Notes / next steps for this POC

- Text extraction is intentionally simple (`pdfplumber`) — swap in
  OCR, LLM summarization, embeddings, etc. inside `process_chunk` in
  `app/tasks.py` without touching the orchestration logic.
- Retries: each chunk task retries up to 2x on failure (transient
  I/O errors, etc.) before failing the whole chord.
- For very large books, consider chunking by token/word count instead
  of fixed page count if pages are uneven in density.

#   D o c - C h u n k i n g  
 