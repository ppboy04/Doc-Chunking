"""
Vector search and semantic analysis utilities.
"""
from typing import List, Dict
from app.database import SessionLocal, semantic_search, search_by_keywords, get_document_summary


def search_documents(query: str, limit: int = 5, threshold: float = 0.5) -> List[Dict]:
    """
    Perform semantic search across all documents.
    
    Args:
        query: Natural language search query
        limit: Maximum number of results
        threshold: Minimum similarity score (0-1)
    
    Returns:
        List of matching document pages with relevance scores
    """
    db = SessionLocal()
    try:
        results = semantic_search(db, query, limit=limit, threshold=threshold)
        return results
    finally:
        db.close()


def search_keywords(keywords: List[str], limit: int = 10) -> List[Dict]:
    """
    Search documents by keywords (pattern matching).
    
    Args:
        keywords: List of search terms
        limit: Maximum results per keyword
    
    Returns:
        Matching passages with keyword context
    """
    db = SessionLocal()
    try:
        results = search_by_keywords(db, keywords, limit=limit)
        return results
    finally:
        db.close()


def get_document_info(document_id: int) -> Dict:
    """Get comprehensive document statistics."""
    db = SessionLocal()
    try:
        return get_document_summary(db, document_id)
    finally:
        db.close()


def compare_documents(query: str, results: List[Dict]) -> Dict:
    """
    Generate comparison analysis between query and search results.
    
    Args:
        query: Original search query
        results: List of search results
    
    Returns:
        Analysis of relevance and relationships
    """
    return {
        "query": query,
        "num_results": len(results),
        "avg_similarity": sum(r.get("similarity", 0) for r in results) / len(results) if results else 0,
        "top_result": results[0] if results else None,
        "results": results,
    }


if __name__ == "__main__":
    # Example usage
    print("🔍 Vector Search Example")
    print("=" * 50)
    
    query = "Bitcoin price prediction"
    results = search_documents(query, limit=5)
    
    print(f"\nQuery: {query}")
    print(f"Results: {len(results)}\n")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. Page {result['page_number']} (Similarity: {result['similarity']:.3f})")
        print(f"   Text: {result['text'][:100]}...")
        print()
