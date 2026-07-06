# 🔍 Vector Search Quick Start

Get semantic search over your PDFs up and running in 5 minutes.

## What is Vector Search?

Vector search lets you find passages by **meaning** rather than keywords:

```
❌ Keyword search: "climate change"  →  Only finds exact phrase
✅ Vector search: "climate change"  →  Also finds: "global warming", "greenhouse gases", "weather patterns"
```

## Quick Start (Docker)

### 1. Start Services

```bash
cd book-chunk-processor
docker compose up --build
```

This starts:
- ✅ PostgreSQL 16 with pgvector
- ✅ Redis (message broker)
- ✅ 3 Celery workers (parallel processing)
- ✅ Flower UI (job monitoring)
- ✅ Your PDF processor

### 2. Process a PDF

```bash
# Copy your PDF to input folder
cp /path/to/your/book.pdf input/book.pdf

# Docker will automatically process it
# Monitor progress: http://localhost:5555 (Flower)
```

### 3. Search Semantically

Once processing is complete:

```bash
# Find similar content by meaning
python search_vectors.py "artificial intelligence and jobs"

# Get top 10 results
python search_vectors.py "climate change impacts" --top-k 10

# Search by keywords
python search_vectors.py --keywords "regulation" "compliance"

# See statistics
python search_vectors.py --stats
```

## Local Setup (No Docker)

### Prerequisites
```bash
# Install PostgreSQL 16
brew install postgresql@16

# Start PostgreSQL
brew services start postgresql@16

# Create database
createdb bookdb

# Install pgvector extension
psql bookdb
postgres=# CREATE EXTENSION IF NOT EXISTS vector;
postgres=# \q
```

### Install & Run

```bash
# Install Python packages
pip install -r requirements.txt

# Initialize database
python setup_database.py --init

# Verify setup
python setup_database.py --test

# Process a PDF
python -m app.main input/book.pdf

# Search
python search_vectors.py "your search query"
```

## How It Works

```
Your PDF
   ↓
[Split into chunks]
   ↓
[Extract text from each page]
   ↓
[Generate 384-dimensional embeddings] ← sentence-transformers model
   ↓
[Store in PostgreSQL with pgvector]
   ↓
[Semantic search using cosine distance]
   ↓
Results ranked by relevance
```

## Example: RAG (Retrieval-Augmented Generation)

Use search results to augment LLM context:

```python
from app.db import SessionLocal, similarity_search
from app.embeddings import embed

# Your question
question = "How does blockchain work?"

# Search for relevant passages
query_embedding = embed(question)
db = SessionLocal()
relevant_pages = similarity_search(db, query_embedding, top_k=5)
db.close()

# Extract text from results
context = "\n".join([p.text for p in relevant_pages])

# Use with ChatGPT / Claude / Llama
prompt = f"""Context: {context}
Question: {question}
Answer:"""

# Call your favorite LLM...
```

## Performance

| Operation | Speed | Notes |
|-----------|-------|-------|
| Embedding 1 page | ~5ms | Uses lightweight model (all-MiniLM-L6-v2) |
| Store in DB | ~1ms | Per page |
| Semantic search | <50ms | For 1M+ vectors with index |
| Processing 100 pages | ~30 seconds | With 3 parallel workers |

## Troubleshooting

### "Connection refused"
```bash
# Check PostgreSQL is running
ps aux | grep postgres

# Or if using Docker
docker compose ps
```

### "pgvector extension not found"
```bash
# Install it
psql bookdb
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

### "EMBEDDING_DIM mismatch"
Ensure environment variable matches model:
```bash
export EMBEDDING_DIM=384  # for all-MiniLM-L6-v2
```

## Environment Variables

```bash
# Database
export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/bookdb"

# Embeddings
export EMBEDDING_MODEL="all-MiniLM-L6-v2"  # lightweight, fast
export EMBEDDING_DIM=384

# Processing
export CHUNK_SIZE=20      # pages per chunk
export INPUT_DIR="./input"
export OUTPUT_DIR="./output"

# Celery/Redis
export REDIS_URL="redis://localhost:6379/0"
```

## Alternative Embedding Models

Want better quality or different language support?

```bash
# High quality (slower, larger)
export EMBEDDING_MODEL="all-mpnet-base-v2"
export EMBEDDING_DIM=768

# Fast, multilingual
export EMBEDDING_MODEL="bge-small-en-v1.5"
export EMBEDDING_DIM=384
```

## Next Steps

1. **Process multiple PDFs** - They'll all be searchable together
2. **Build a web UI** - Use FastAPI + React to search
3. **Add reranking** - Use cross-encoder for better relevance
4. **Connect to LLM** - Build RAG chatbot
5. **Add caching** - Speed up repeated searches

## Architecture Diagram

```
┌─────────────────┐
│   Input PDF     │
└────────┬────────┘
         │
    ┌────▼─────┐
    │ Chunker  │  ← Split into 20-page chunks
    └────┬─────┘
         │
    ┌────▼──────────────────────────┐
    │   Celery Chord (Fan-out)      │
    └────┬──────────────────────────┘
         │
    ┌────┴────────────────────────────┐
    │                                 │
┌───▼──────┐  ┌───────────┐  ┌───────▼───┐
│ Worker 1 │  │ Worker 2  │  │ Worker 3  │
└───┬──────┘  └───────────┘  └───────────┘
    │                                 │
    │ 1. Extract text (pdfplumber)   │
    │ 2. Generate embeddings         │
    │ 3. Store + pgvector vectors    │
    │                                 │
    └────┬────────────────────────────┘
         │
    ┌────▼─────────────────┐
    │ PostgreSQL + pgvector│  ← Semantic search index
    └─────────────────────┘
         │
    ┌────▼──────────────────┐
    │ Merge Results (JSON)  │
    └───────────────────────┘
```

## Support

- 📖 Full guide: [VECTOR_SEARCH_GUIDE.md](./VECTOR_SEARCH_GUIDE.md)
- 🔧 Setup help: `python setup_database.py --help`
- 🔍 Search help: `python search_vectors.py --help`
- 📊 Status: `python search_vectors.py --stats`
