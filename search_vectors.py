"""
Semantic search CLI for querying stored PDF embeddings.

Usage:
    python search_vectors.py "your search query"
    python search_vectors.py --keywords "bitcoin" "price" "forecast"
    python search_vectors.py --list-documents
"""
import sys
import argparse
from app.db import SessionLocal, similarity_search
from app.embeddings import embed


def search_semantic(query: str, top_k: int = 5):
    """Perform semantic search on embeddings."""
    print(f"\n🔍 Semantic Search: {query}")
    print("=" * 70)
    
    query_embedding = embed(query)
    db = SessionLocal()
    
    try:
        results = similarity_search(db, query_embedding, top_k=top_k)
        
        if not results:
            print("❌ No results found.")
            return
        
        print(f"✓ Found {len(results)} results:\n")
        
        for i, result in enumerate(results, 1):
            print(f"{i}. Page {result.page_number} | Chunk {result.chunk_id}")
            print(f"   File: {result.source_file}")
            print(f"   Words: {result.word_count}")
            print(f"   Text: {result.text[:150]}...")
            print()
    
    finally:
        db.close()


def search_keywords(keywords: list[str], source_file: str = None):
    """Search by keywords (pattern matching)."""
    print(f"\n🔎 Keyword Search: {', '.join(keywords)}")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        from sqlalchemy import or_
        from app.db import PageChunk
        
        # Build OR query for keywords
        filters = [PageChunk.text.ilike(f"%{kw}%") for kw in keywords]
        query = db.query(PageChunk)
        
        if source_file:
            query = query.filter(PageChunk.source_file == source_file)
        
        results = query.filter(or_(*filters)).limit(10).all()
        
        if not results:
            print("❌ No results found.")
            return
        
        print(f"✓ Found {len(results)} results:\n")
        
        for i, result in enumerate(results, 1):
            print(f"{i}. Page {result.page_number} | {result.source_file}")
            print(f"   {result.text[:100]}...")
            print()
    
    finally:
        db.close()


def list_documents(source_file: str = None):
    """List all documents in database."""
    print(f"\n📚 Documents in Database")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        from app.db import PageChunk
        
        query = db.query(PageChunk.source_file).distinct()
        documents = query.all()
        
        if not documents:
            print("❌ No documents found.")
            return
        
        print(f"✓ Found {len(documents)} unique documents:\n")
        
        for doc in documents:
            # Count pages per document
            count = db.query(PageChunk).filter(
                PageChunk.source_file == doc[0]
            ).count()
            print(f"  • {doc[0]} ({count} pages)")
    
    finally:
        db.close()


def show_stats():
    """Show database statistics."""
    print(f"\n📊 Database Statistics")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        from app.db import PageChunk
        
        total_pages = db.query(PageChunk).count()
        unique_docs = db.query(PageChunk.source_file).distinct().count()
        total_words = db.query(PageChunk.word_count).all()
        total_word_count = sum(w[0] for w in total_words if w[0])
        
        print(f"✓ Total Pages:        {total_pages}")
        print(f"✓ Unique Documents:   {unique_docs}")
        print(f"✓ Total Words:        {total_word_count:,}")
        print()
    
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Semantic search over PDF embeddings stored in pgvector"
    )
    parser.add_argument("query", nargs="?", help="Semantic search query")
    parser.add_argument("--keywords", nargs="+", help="Keyword search")
    parser.add_argument("--list-documents", action="store_true", help="List all documents")
    parser.add_argument("--stats", action="store_true", help="Show database stats")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--source", help="Filter by source file")
    
    args = parser.parse_args()
    
    try:
        if args.list_documents:
            list_documents()
        elif args.stats:
            show_stats()
        elif args.keywords:
            search_keywords(args.keywords, source_file=args.source)
        elif args.query:
            search_semantic(args.query, top_k=args.top_k)
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Search cancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
