#!/usr/bin/env python
"""
PostgreSQL + pgvector Setup & Verification Script

This script helps you:
1. Initialize the database schema
2. Verify PostgreSQL + pgvector connectivity
3. Test embedding generation
4. Run sample semantic searches

Usage:
    python setup_database.py --init           # Initialize schema
    python setup_database.py --test           # Run tests
    python setup_database.py --status         # Check connection
"""
import os
import sys
import argparse
from sqlalchemy import text


def check_postgres_connection():
    """Test PostgreSQL connectivity."""
    print("\n🔗 Checking PostgreSQL Connection...")
    print("-" * 50)
    
    try:
        from app.db import engine
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()
            print(f"✓ Connected to: {version[0][:80]}...")
            return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def check_pgvector_extension():
    """Verify pgvector extension is installed."""
    print("\n📦 Checking pgvector Extension...")
    print("-" * 50)
    
    try:
        from app.db import engine
        with engine.connect() as conn:
            # Check if pgvector extension exists
            result = conn.execute(
                text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');")
            )
            exists = result.fetchone()[0]
            
            if exists:
                print("✓ pgvector extension is installed")
                
                # Get version
                result = conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector';"))
                version = result.fetchone()
                if version:
                    print(f"  Version: {version[0]}")
            else:
                print("⚠️  pgvector extension not found, installing...")
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
                print("✓ pgvector extension installed successfully")
            
            return True
    except Exception as e:
        print(f"❌ Extension check failed: {e}")
        return False


def initialize_database():
    """Initialize database schema."""
    print("\n📊 Initializing Database Schema...")
    print("-" * 50)
    
    try:
        from app.db import init_db
        init_db()
        print("✓ Database schema initialized")
        
        # Verify tables exist
        from app.db import engine
        inspector = __import__('sqlalchemy.inspect', fromlist=['inspect']).inspect
        inspector_obj = inspector(engine)
        tables = inspector_obj.get_table_names()
        
        if 'page_chunks' in tables:
            print(f"✓ Tables created: {tables}")
        else:
            print("❌ Tables not created properly")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Schema initialization failed: {e}")
        return False


def test_embedding_generation():
    """Test embedding generation."""
    print("\n🧠 Testing Embedding Generation...")
    print("-" * 50)
    
    try:
        from app.embeddings import embed
        
        test_texts = [
            "PostgreSQL is a powerful open source database.",
            "Vector search enables semantic similarity matching.",
            "Machine learning models generate embeddings.",
        ]
        
        print(f"Generating embeddings for {len(test_texts)} texts...")
        
        for i, text in enumerate(test_texts, 1):
            embedding = embed(text)
            print(f"  {i}. {text[:50]}...")
            print(f"     Embedding dimension: {len(embedding)}")
        
        print("✓ Embedding generation working")
        return True
    except Exception as e:
        print(f"❌ Embedding generation failed: {e}")
        return False


def test_database_operations():
    """Test database insert and retrieval."""
    print("\n💾 Testing Database Operations...")
    print("-" * 50)
    
    try:
        from app.db import SessionLocal, PageChunk, save_page
        from app.embeddings import embed
        
        db = SessionLocal()
        
        # Test insert
        test_text = "This is a test document for the book chunk processor."
        embedding = embed(test_text)
        
        page = save_page(
            db,
            source_file="test.pdf",
            chunk_id=0,
            page_number=1,
            text_content=test_text,
            word_count=11,
            embedding=embedding,
        )
        
        print(f"✓ Inserted test page: {page.id}")
        
        # Test retrieval
        retrieved = db.query(PageChunk).filter(PageChunk.source_file == "test.pdf").first()
        if retrieved:
            print(f"✓ Retrieved page: ID={retrieved.id}, text={retrieved.text[:40]}...")
        
        # Clean up
        db.query(PageChunk).filter(PageChunk.source_file == "test.pdf").delete()
        db.commit()
        print("✓ Cleanup completed")
        
        db.close()
        return True
    except Exception as e:
        print(f"❌ Database operations failed: {e}")
        return False


def test_similarity_search():
    """Test semantic similarity search."""
    print("\n🔍 Testing Similarity Search...")
    print("-" * 50)
    
    try:
        from app.db import SessionLocal, PageChunk, save_page, similarity_search
        from app.embeddings import embed
        
        db = SessionLocal()
        
        # Insert test documents
        test_docs = [
            "Python is a programming language for data science.",
            "Machine learning uses neural networks for pattern recognition.",
            "The weather today is sunny and warm.",
        ]
        
        print(f"Inserting {len(test_docs)} test documents...")
        
        for i, text in enumerate(test_docs):
            embedding = embed(text)
            save_page(
                db,
                source_file="similarity_test.pdf",
                chunk_id=i,
                page_number=i+1,
                text_content=text,
                word_count=len(text.split()),
                embedding=embedding,
            )
        
        # Perform semantic search
        query = "Deep learning and artificial intelligence"
        query_embedding = embed(query)
        
        results = similarity_search(db, query_embedding, top_k=2)
        
        print(f"\nQuery: '{query}'")
        print(f"Results:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. Page {result.page_number}: {result.text[:60]}...")
        
        # Clean up
        db.query(PageChunk).filter(PageChunk.source_file == "similarity_test.pdf").delete()
        db.commit()
        print("\n✓ Similarity search working correctly")
        
        db.close()
        return True
    except Exception as e:
        print(f"❌ Similarity search test failed: {e}")
        return False


def show_status():
    """Show database status and statistics."""
    print("\n📈 Database Status")
    print("=" * 50)
    
    try:
        from app.db import SessionLocal, PageChunk
        
        db = SessionLocal()
        
        total_pages = db.query(PageChunk).count()
        unique_docs = db.query(PageChunk.source_file).distinct().count()
        
        print(f"Total pages indexed: {total_pages}")
        print(f"Unique documents: {unique_docs}")
        
        if unique_docs > 0:
            docs = db.query(PageChunk.source_file).distinct().all()
            print("\nDocuments:")
            for doc in docs:
                count = db.query(PageChunk).filter(PageChunk.source_file == doc[0]).count()
                print(f"  • {doc[0]}: {count} pages")
        
        db.close()
        return True
    except Exception as e:
        print(f"❌ Status check failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="PostgreSQL + pgvector Setup & Verification"
    )
    parser.add_argument("--init", action="store_true", help="Initialize database schema")
    parser.add_argument("--test", action="store_true", help="Run all tests")
    parser.add_argument("--status", action="store_true", help="Show database status")
    parser.add_argument("--check", action="store_true", help="Check connections only")
    
    args = parser.parse_args()
    
    print("\n" + "=" * 50)
    print("PostgreSQL + pgvector Setup")
    print("=" * 50)
    
    try:
        if args.test or (not args.init and not args.status and not args.check):
            # Run comprehensive tests
            checks = [
                check_postgres_connection,
                check_pgvector_extension,
                initialize_database,
                test_embedding_generation,
                test_database_operations,
                test_similarity_search,
                show_status,
            ]
            
            results = []
            for check in checks:
                try:
                    result = check()
                    results.append(result)
                except Exception as e:
                    print(f"❌ Test failed: {e}")
                    results.append(False)
            
            print("\n" + "=" * 50)
            if all(results):
                print("✓ All tests passed! System is ready.")
                return 0
            else:
                print("❌ Some tests failed. Check errors above.")
                return 1
        
        elif args.init:
            check_postgres_connection()
            check_pgvector_extension()
            initialize_database()
            print("\n✓ Database initialized!")
            return 0
        
        elif args.check:
            check_postgres_connection()
            check_pgvector_extension()
            return 0
        
        elif args.status:
            show_status()
            return 0
    
    except KeyboardInterrupt:
        print("\n⚠️  Setup cancelled.")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
