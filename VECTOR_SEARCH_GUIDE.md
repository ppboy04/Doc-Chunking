# PostgreSQL + pgvector Integration Guide

## Overview

This guide explains how the Book Chunk Processor uses PostgreSQL and pgvector for semantic vector search over extracted PDF content.

## Architecture

```
PDF Processing Pipeline
        ↓
   [Chunking] (split into 20-page chunks)
        ↓
   [Text Extraction] (pdfplumber)
        ↓
   [Embedding Generation] (sentence-transformers: all-MiniLM-L6-v2)
        ↓
   [pgvector Storage] (PostgreSQL vector columns)
        ↓
   [Semantic Search] (cosine distance similarity)
```

## Components

### 1. Database Models (`app/db.py`)

**PageChunk Table**
```sql
CREATE TABLE page_chunks (
    id SERIAL PRIMARY KEY,
    source_file VARCHAR NOT NULL,
    chunk_id INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    word_count INTEGER DEFAULT 0,
    text TEXT NOT NULL,
    embedding vector(384)  -- 384-dimensional vector
);
```

### 2. Embedding Generation (`app/embeddings.py`)

Uses `sentence-transformers` library with the `all-MiniLM-L6-v2` model:
- **Model**: all-MiniLM-L6-v2
- **Dimension**: 384
- **Speed**: ~100+ documents/second on CPU
- **Quality**: Excellent for semantic similarity tasks
- **Local**: No API keys required, runs on your hardware

```python
from app.embeddings import embed

text = "The future of artificial intelligence in healthcare"
embedding = embed(text)  # Returns 384-dimensional vector
```

### 3. Semantic Search (`app/db.py`)

Uses pgvector's cosine distance operator (`<=>`):

```python
from app.db import SessionLocal, similarity_search
from app.embeddings import embed

query_embedding = embed("machine learning applications")
db = SessionLocal()
results = similarity_search(db, query_embedding, top_k=5)
db.close()

for result in results:
    print(f"Page {result.page_number}: {result.text[:100]}...")
    print(f"Similarity: {result.embedding_similarity}")
```

## Setup Instructions

### Option 1: Using Docker (Recommended)

```bash
# 1. Build and start services
docker compose up --build

# 2. Initialize database (runs automatically)
python setup_database.py --init

# 3. Process a PDF
cp your-book.pdf input/book.pdf
docker compose up

# 4. Search embeddings
python search_vectors.py "your search query"
```

### Option 2: Local Development

#### Prerequisites
- PostgreSQL 16+ with pgvector extension
- Python 3.8+
- Redis (for Celery, optional for standalone processing)

#### Installation

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Install PostgreSQL (macOS)
brew install postgresql@16
brew services start postgresql@16

# Create database
createdb bookdb

# 3. Install pgvector extension
psql bookdb -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 4. Initialize database schema
python setup_database.py --init

# 5. Verify setup
python setup_database.py --test
```

### Option 3: Docker Database Only + Local Python

```bash
# Start PostgreSQL in Docker
docker run --name pgvector-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=bookdb \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Set environment variable
export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/bookdb"

# Install Python packages
pip install -r requirements.txt

# Initialize schema
python setup_database.py --init

# Process PDFs
python -m app.main input/book.pdf

# Search
python search_vectors.py "your query"
```

## Usage Examples

### 1. Semantic Search CLI

```bash
# Search for similar content
python search_vectors.py "natural language processing"

# Top 10 results
python search_vectors.py "deep learning" --top-k 10

# Filter by source file
python search_vectors.py "quantum computing" --source physics-book.pdf

# Keyword search
python search_vectors.py --keywords "bitcoin" "cryptocurrency" "blockchain"

# List all documents
python search_vectors.py --list-documents

# Database statistics
python search_vectors.py --stats
```

### 2. Programmatic Search

```python
#!/usr/bin/env python
"""Example: RAG (Retrieval-Augmented Generation) Pattern"""
from app.db import SessionLocal, similarity_search
from app.embeddings import embed

# Your question
question = "What are the benefits of machine learning in healthcare?"

# 1. Embed the question
query_embedding = embed(question)

# 2. Retrieve relevant documents
db = SessionLocal()
relevant_docs = similarity_search(db, query_embedding, top_k=5)
db.close()

# 3. Use with LLM (pseudo-code)
context = "\n".join([d.text for d in relevant_docs])

prompt = f"""
Based on the following context, answer the question:

Context:
{context}

Question: {question}

Answer:
"""

# Call your LLM here (OpenAI, Claude, Llama, etc.)
```

### 3. Processing New PDFs with Vector Storage

```bash
# Automatic: PDF → Chunks → Embeddings → PostgreSQL
python -m app.main data/new-book.pdf

# With custom chunk size
export CHUNK_SIZE=10
python -m app.main data/new-book.pdf

# Using Celery with workers
celery -A app.celery_app worker --loglevel=info &
python -m app.main data/new-book.pdf
```

## Configuration

Set environment variables in `.env` or via `export`:

```bash
# Chunk size (pages per chunk)
export CHUNK_SIZE=20

# Database connection
export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/bookdb"

# Embedding model
export EMBEDDING_MODEL="all-MiniLM-L6-v2"
export EMBEDDING_DIM=384

# Paths
export INPUT_DIR="./input"
export OUTPUT_DIR="./output"

# Redis (for Celery)
export REDIS_URL="redis://localhost:6379/0"
```

## Embedding Models Comparison

| Model | Dimension | Speed | Quality | Size |
|-------|-----------|-------|---------|------|
| all-MiniLM-L6-v2 | 384 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 22MB |
| all-mpnet-base-v2 | 768 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 430MB |
| all-distilroberta-v1 | 768 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 250MB |
| bge-small-en-v1.5 | 384 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 33MB |

**Recommended**: `all-MiniLM-L6-v2` for fast, accurate semantic search.

To use a different model:

```bash
export EMBEDDING_MODEL="all-mpnet-base-v2"
export EMBEDDING_DIM=768  # Update dimension to match
```

## Performance Metrics

### Embedding Generation
- **Speed**: ~100-150 documents/second (CPU)
- **Model**: all-MiniLM-L6-v2
- **Memory**: ~500MB per worker
- **First run**: ~500ms (model loading)

### Similarity Search
- **Index type**: pgvector (L2, cosine, inner product)
- **Query time**: <10ms for 1M vectors (with HNSW index)
- **Accuracy**: High recall for semantic similarity

### Database Performance
- **Inserts**: 1000+ pages/second
- **Queries**: <50ms for top-10 results
- **Storage**: ~1.5KB per embedding (384-dim vector)

## Creating Indexes for Performance

```python
from sqlalchemy import text
from app.db import engine

# Create HNSW index for faster similarity search
with engine.connect() as conn:
    conn.execute(text("""
        CREATE INDEX ON page_chunks 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """))
    conn.commit()
```

## Troubleshooting

### 1. "pgvector extension not found"

```bash
# Connect to your database
psql bookdb

# Create extension
CREATE EXTENSION IF NOT EXISTS vector;
```

### 2. "Connection refused" to PostgreSQL

Check if PostgreSQL is running:
```bash
# Docker
docker compose logs postgres

# Local macOS
brew services list | grep postgresql

# Linux
sudo systemctl status postgresql
```

### 3. Slow similarity search

Add an index:
```python
from app.db import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("""
        CREATE INDEX embedding_idx ON page_chunks 
        USING hnsw (embedding vector_cosine_ops)
    """))
    conn.commit()
```

### 4. "EMBEDDING_DIM mismatch"

Ensure `EMBEDDING_DIM` matches your model:
- `all-MiniLM-L6-v2`: 384
- `all-mpnet-base-v2`: 768
- `all-distilroberta-v1`: 768

```bash
# Check current setting
echo $EMBEDDING_DIM

# Update if needed
export EMBEDDING_DIM=384
```

## Advanced: Custom Similarity Queries

```python
from sqlalchemy import desc
from app.db import SessionLocal, PageChunk

db = SessionLocal()

# Raw SQL with pgvector
query = """
SELECT 
    page_number, 
    source_file, 
    text,
    1 - (embedding <=> %s) as similarity
FROM page_chunks
WHERE source_file = %s
ORDER BY embedding <=> %s
LIMIT 10;
"""

# Using SQLAlchemy ORM
from app.embeddings import embed
query_vec = embed("your query")

results = db.query(PageChunk).order_by(
    PageChunk.embedding.cosine_distance(query_vec)
).filter(
    PageChunk.source_file == "book.pdf"
).limit(10).all()

db.close()
```

## Next Steps

1. **Implement RAG**: Use search results as context for LLMs
2. **Add Reranking**: Use a cross-encoder to rerank results
3. **Semantic Clustering**: Group documents by topic using embeddings
4. **Named Entity Recognition**: Extract key terms from search results
5. **Multi-modal Search**: Add image/table embeddings

## References

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [sentence-transformers](https://www.sbert.net/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [PostgreSQL Vector Search](https://supabase.com/docs/guides/database/extensions/pgvector)
