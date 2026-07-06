"""
PostgreSQL + pgvector database module for storing and searching PDF embeddings.
"""
import os
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pgvector.sqlalchemy import Vector
from datetime import datetime
from sentence_transformers import SentenceTransformer

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/bookdb")

# SQLAlchemy setup
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Initialize embedding model (768-dimensional embeddings from all-MiniLM-L6-v2)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
EMBEDDING_DIMENSION = 384  # MiniLM produces 384-dim embeddings


class Document(Base):
    """Document metadata table."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    source_file = Column(String(255), index=True)
    chunk_id = Column(Integer, index=True)
    start_page = Column(Integer)
    end_page = Column(Integer)
    word_count = Column(Integer)
    char_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ChunkEmbedding(Base):
    """Table for storing chunk embeddings with pgvector."""
    __tablename__ = "chunk_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, index=True)
    page_number = Column(Integer)
    text = Column(Text)
    embedding = Column(Vector(EMBEDDING_DIMENSION), index=True)
    word_count = Column(Integer)
    char_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class PageEmbedding(Base):
    """Table for storing page-level embeddings."""
    __tablename__ = "page_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, index=True)
    page_number = Column(Integer, index=True)
    chunk_id = Column(Integer, index=True)
    text = Column(Text)
    embedding = Column(Vector(EMBEDDING_DIMENSION), index=True)
    word_count = Column(Integer)
    char_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables initialized")


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def store_document_metadata(
    db: Session,
    source_file: str,
    chunk_id: int,
    start_page: int,
    end_page: int,
    word_count: int,
    char_count: int
) -> Document:
    """Store document chunk metadata."""
    doc = Document(
        source_file=source_file,
        chunk_id=chunk_id,
        start_page=start_page,
        end_page=end_page,
        word_count=word_count,
        char_count=char_count,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def store_page_embedding(
    db: Session,
    document_id: int,
    page_number: int,
    chunk_id: int,
    text: str,
    word_count: int,
    char_count: int
) -> PageEmbedding:
    """Generate embedding for page text and store in database."""
    # Generate embedding
    embedding = embedding_model.encode(text, convert_to_numpy=False).tolist()
    
    # Truncate text if too long
    text_to_store = text[:5000] if len(text) > 5000 else text
    
    # Store in database
    page_emb = PageEmbedding(
        document_id=document_id,
        page_number=page_number,
        chunk_id=chunk_id,
        text=text_to_store,
        embedding=embedding,
        word_count=word_count,
        char_count=char_count,
    )
    db.add(page_emb)
    db.commit()
    db.refresh(page_emb)
    return page_emb


def store_chunk_embedding(
    db: Session,
    document_id: int,
    page_number: int,
    text: str,
    word_count: int,
    char_count: int
) -> ChunkEmbedding:
    """Generate embedding for chunk text and store in database."""
    # Generate embedding
    embedding = embedding_model.encode(text, convert_to_numpy=False).tolist()
    
    # Truncate text if too long
    text_to_store = text[:5000] if len(text) > 5000 else text
    
    # Store in database
    chunk_emb = ChunkEmbedding(
        document_id=document_id,
        page_number=page_number,
        text=text_to_store,
        embedding=embedding,
        word_count=word_count,
        char_count=char_count,
    )
    db.add(chunk_emb)
    db.commit()
    db.refresh(chunk_emb)
    return chunk_emb


def semantic_search(
    db: Session,
    query: str,
    limit: int = 5,
    threshold: float = 0.5
) -> List[dict]:
    """
    Perform semantic search on stored documents using vector similarity.
    
    Args:
        db: Database session
        query: Search query text
        limit: Maximum number of results
        threshold: Minimum similarity score (0-1)
    
    Returns:
        List of matching documents with similarity scores
    """
    # Generate query embedding
    query_embedding = embedding_model.encode(query, convert_to_numpy=False).tolist()
    
    # Search for similar embeddings using cosine similarity
    # PostgreSQL pgvector uses <=> for cosine distance (1 - similarity)
    results = db.query(
        PageEmbedding,
        (1 - (PageEmbedding.embedding.cosine_distance(query_embedding))).label("similarity")
    ).filter(
        (1 - (PageEmbedding.embedding.cosine_distance(query_embedding))) >= threshold
    ).order_by(
        PageEmbedding.embedding.cosine_distance(query_embedding)
    ).limit(limit).all()
    
    # Format results
    formatted_results = []
    for page_emb, similarity in results:
        formatted_results.append({
            "page_number": page_emb.page_number,
            "chunk_id": page_emb.chunk_id,
            "text": page_emb.text,
            "similarity": float(similarity),
            "word_count": page_emb.word_count,
            "created_at": page_emb.created_at.isoformat(),
        })
    
    return formatted_results


def get_document_summary(db: Session, document_id: int) -> dict:
    """Get summary statistics for a document."""
    pages = db.query(PageEmbedding).filter(
        PageEmbedding.document_id == document_id
    ).all()
    
    if not pages:
        return {}
    
    total_pages = len(pages)
    total_words = sum(p.word_count for p in pages)
    total_chars = sum(p.char_count for p in pages)
    
    return {
        "document_id": document_id,
        "total_pages": total_pages,
        "total_words": total_words,
        "total_chars": total_chars,
    }


def search_by_keywords(
    db: Session,
    keywords: List[str],
    limit: int = 10
) -> List[dict]:
    """
    Search by keywords using full-text search (basic pattern matching).
    """
    results = []
    for keyword in keywords:
        pattern = f"%{keyword}%"
        matches = db.query(PageEmbedding).filter(
            PageEmbedding.text.ilike(pattern)
        ).limit(limit).all()
        
        for match in matches:
            results.append({
                "page_number": match.page_number,
                "keyword": keyword,
                "text": match.text[:200] + "...",
                "created_at": match.created_at.isoformat(),
            })
    
    return results


def get_trending_topics(db: Session, limit: int = 10) -> List[dict]:
    """Get most recent documents/chunks added."""
    recent = db.query(PageEmbedding).order_by(
        PageEmbedding.created_at.desc()
    ).limit(limit).all()
    
    return [
        {
            "page_number": p.page_number,
            "chunk_id": p.chunk_id,
            "word_count": p.word_count,
            "created_at": p.created_at.isoformat(),
        }
        for p in recent
    ]
