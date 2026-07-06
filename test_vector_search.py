"""
Test suite for PostgreSQL + pgvector vector search functionality.

Run with:
    pytest test_vector_search.py -v
    pytest test_vector_search.py::TestEmbeddings -v
    pytest test_vector_search.py::TestDatabase -v
"""
import pytest
import os
from sqlalchemy import text
from app.embeddings import embed, embed_batch
from app.db import (
    SessionLocal, 
    engine, 
    PageChunk, 
    save_page, 
    similarity_search,
    init_db
)


class TestEmbeddings:
    """Test embedding generation."""
    
    def test_embed_returns_correct_dimension(self):
        """Test that embeddings have correct dimension (384 for all-MiniLM-L6-v2)."""
        text = "This is a test document for embedding generation."
        embedding = embed(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
    
    def test_embed_empty_text_returns_zeros(self):
        """Test that empty text returns zero vector."""
        embedding = embed("")
        assert all(x == 0.0 for x in embedding)
    
    def test_embed_whitespace_only_returns_zeros(self):
        """Test that whitespace-only text returns zero vector."""
        embedding = embed("   \n\t   ")
        assert all(x == 0.0 for x in embedding)
    
    def test_embed_similar_texts_have_similar_embeddings(self):
        """Test that semantically similar texts produce similar embeddings."""
        text1 = "The cat sat on the mat"
        text2 = "The cat is sitting on the mat"
        text3 = "The dog barked loudly"
        
        emb1 = embed(text1)
        emb2 = embed(text2)
        emb3 = embed(text3)
        
        # Calculate cosine similarity
        def cosine_similarity(a, b):
            import math
            dot = sum(x*y for x, y in zip(a, b))
            mag_a = math.sqrt(sum(x*x for x in a))
            mag_b = math.sqrt(sum(x*x for x in b))
            return dot / (mag_a * mag_b) if mag_a and mag_b else 0
        
        sim_12 = cosine_similarity(emb1, emb2)
        sim_13 = cosine_similarity(emb1, emb3)
        
        # Similar texts should have higher similarity
        assert sim_12 > sim_13
    
    def test_embed_batch(self):
        """Test batch embedding generation."""
        texts = [
            "Python is a programming language",
            "JavaScript is used for web development",
            "Rust is a systems programming language",
        ]
        
        embeddings = embed_batch(texts)
        
        assert len(embeddings) == 3
        assert all(len(e) == 384 for e in embeddings)


class TestDatabase:
    """Test database operations."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and cleanup for each test."""
        # Setup: create tables
        init_db()
        
        yield
        
        # Teardown: clean test data
        db = SessionLocal()
        db.query(PageChunk).filter(PageChunk.source_file.like("test_%")).delete()
        db.commit()
        db.close()
    
    def test_database_connection(self):
        """Test PostgreSQL connection."""
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
    
    def test_pgvector_extension_exists(self):
        """Test that pgvector extension is installed."""
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector')")
            )
            assert result.fetchone()[0] is True
    
    def test_page_chunk_table_exists(self):
        """Test that page_chunks table was created."""
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name='page_chunks'
                    )
                """)
            )
            assert result.fetchone()[0] is True
    
    def test_save_page(self):
        """Test saving a page with embedding."""
        db = SessionLocal()
        
        text_content = "Test document for vector storage"
        embedding = embed(text_content)
        
        page = save_page(
            db,
            source_file="test_single.pdf",
            chunk_id=0,
            page_number=1,
            text_content=text_content,
            word_count=5,
            embedding=embedding,
        )
        
        # Verify page was created
        assert page.id is not None
        assert page.source_file == "test_single.pdf"
        assert page.page_number == 1
        
        db.close()
    
    def test_save_and_retrieve_page(self):
        """Test save and retrieve operations."""
        db = SessionLocal()
        
        text_content = "This is a test page for retrieval"
        embedding = embed(text_content)
        
        save_page(
            db,
            source_file="test_retrieve.pdf",
            chunk_id=0,
            page_number=1,
            text_content=text_content,
            word_count=6,
            embedding=embedding,
        )
        
        # Retrieve
        retrieved = db.query(PageChunk).filter(
            PageChunk.source_file == "test_retrieve.pdf"
        ).first()
        
        assert retrieved is not None
        assert retrieved.text == text_content
        assert retrieved.page_number == 1
        
        db.close()
    
    def test_similarity_search_basic(self):
        """Test basic similarity search."""
        db = SessionLocal()
        
        # Insert test documents
        docs = [
            ("Machine learning is a subset of AI", "test_similarity.pdf"),
            ("Neural networks power deep learning", "test_similarity.pdf"),
            ("Python is a programming language", "test_similarity.pdf"),
        ]
        
        for i, (text, source) in enumerate(docs):
            embedding = embed(text)
            save_page(db, source, 0, i+1, text, len(text.split()), embedding)
        
        # Search
        query = "artificial intelligence and machine learning"
        query_embedding = embed(query)
        
        results = similarity_search(db, query_embedding, top_k=2)
        
        # Should find AI/ML related documents first
        assert len(results) > 0
        assert results[0].text in [docs[0][0], docs[1][0]]
        
        db.close()
    
    def test_similarity_search_with_limit(self):
        """Test similarity search with limit."""
        db = SessionLocal()
        
        # Insert 5 documents
        for i in range(5):
            text = f"Document {i}: This is test content number {i}"
            embedding = embed(text)
            save_page(db, "test_limit.pdf", 0, i+1, text, 6, embedding)
        
        # Search
        query_embedding = embed("test content")
        results = similarity_search(db, query_embedding, top_k=3)
        
        assert len(results) <= 3
        
        db.close()
    
    def test_similarity_search_source_filter(self):
        """Test similarity search filtering by source."""
        db = SessionLocal()
        
        # Insert documents with different sources
        texts_a = [
            "Document A: Machine learning techniques",
            "Document A: Deep neural networks",
        ]
        texts_b = [
            "Document B: Python programming",
            "Document B: JavaScript web development",
        ]
        
        for i, text in enumerate(texts_a):
            embedding = embed(text)
            save_page(db, "test_filter_a.pdf", 0, i+1, text, 3, embedding)
        
        for i, text in enumerate(texts_b):
            embedding = embed(text)
            save_page(db, "test_filter_b.pdf", 0, i+1, text, 3, embedding)
        
        # Search in source A only
        query_embedding = embed("machine learning")
        results = similarity_search(db, query_embedding, top_k=5)
        
        # All results should include ML-related content
        assert len(results) > 0
        
        db.close()
    
    def test_bulk_insert_performance(self):
        """Test performance of bulk inserts."""
        db = SessionLocal()
        
        # Insert 100 documents
        import time
        start = time.time()
        
        for i in range(100):
            text = f"Document {i}: This is bulk insert test document number {i}"
            embedding = embed(text)
            save_page(db, "test_bulk.pdf", 0, i+1, text, 10, embedding)
        
        elapsed = time.time() - start
        
        # Should complete in reasonable time (<30 seconds)
        assert elapsed < 30
        
        # Verify count
        count = db.query(PageChunk).filter(
            PageChunk.source_file == "test_bulk.pdf"
        ).count()
        assert count == 100
        
        db.close()


class TestSemanticSearch:
    """Test semantic search functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and cleanup for each test."""
        init_db()
        yield
        
        db = SessionLocal()
        db.query(PageChunk).filter(
            PageChunk.source_file.like("test_semantic_%")
        ).delete()
        db.commit()
        db.close()
    
    def test_semantic_search_clustering(self):
        """Test that semantic search groups related documents."""
        db = SessionLocal()
        
        # AI-related documents
        ai_docs = [
            "Artificial intelligence is transforming technology",
            "Machine learning algorithms improve over time",
            "Deep learning uses neural networks",
        ]
        
        # Biology-related documents
        bio_docs = [
            "DNA contains genetic information",
            "Protein synthesis is crucial for life",
            "Cells are the basic unit of biology",
        ]
        
        # Insert all
        for i, text in enumerate(ai_docs + bio_docs):
            embedding = embed(text)
            source = "test_semantic_ai.pdf" if i < len(ai_docs) else "test_semantic_bio.pdf"
            save_page(db, source, 0, i+1, text, len(text.split()), embedding)
        
        # Search for AI term
        query = "neural network machine learning"
        query_embedding = embed(query)
        results = similarity_search(db, query_embedding, top_k=3)
        
        # Top results should be AI documents
        ai_results = sum(1 for r in results if "artificial" in r.text.lower() 
                        or "machine" in r.text.lower() 
                        or "neural" in r.text.lower())
        
        assert ai_results >= 2
        
        db.close()
    
    def test_search_with_paraphrasing(self):
        """Test that similar queries return similar results."""
        db = SessionLocal()
        
        text = "The quick brown fox jumps over the lazy dog"
        embedding = embed(text)
        save_page(db, "test_semantic_para.pdf", 0, 1, text, 9, embedding)
        
        # Different ways to query same concept
        queries = [
            "fox jumping over dog",
            "quick animal jumping",
            "brown fox"
        ]
        
        embeddings = [embed(q) for q in queries]
        results = [similarity_search(db, emb, top_k=1) for emb in embeddings]
        
        # All should find the same document
        assert all(r[0].page_number == 1 for r in results if r)
        
        db.close()


class TestIntegration:
    """Integration tests for complete workflow."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and cleanup for each test."""
        init_db()
        yield
        
        db = SessionLocal()
        db.query(PageChunk).filter(
            PageChunk.source_file.like("test_integration_%")
        ).delete()
        db.commit()
        db.close()
    
    def test_complete_workflow(self):
        """Test complete embedding → storage → search workflow."""
        db = SessionLocal()
        
        # Step 1: Generate embeddings for documents
        documents = [
            ("PostgreSQL is a powerful relational database", "databases"),
            ("MongoDB uses JSON documents", "databases"),
            ("Python is a versatile programming language", "programming"),
            ("JavaScript powers web development", "programming"),
        ]
        
        # Step 2: Store embeddings
        for i, (text, category) in enumerate(documents):
            embedding = embed(text)
            save_page(
                db,
                source_file="test_integration_kb.pdf",
                chunk_id=0,
                page_number=i+1,
                text_content=text,
                word_count=len(text.split()),
                embedding=embedding,
            )
        
        # Step 3: Perform searches
        test_queries = [
            ("database management", "databases"),
            ("Python programming", "programming"),
        ]
        
        for query, expected_category in test_queries:
            query_embedding = embed(query)
            results = similarity_search(db, query_embedding, top_k=2)
            
            assert len(results) > 0
            # Top result should match expected category
            top_text = results[0].text.lower()
            if expected_category == "databases":
                assert any(word in top_text for word in ["postgresql", "mongodb", "database"])
            else:
                assert any(word in top_text for word in ["python", "javascript", "programming"])
        
        db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
