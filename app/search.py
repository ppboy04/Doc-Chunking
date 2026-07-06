"""
Semantic search over everything that's been embedded into Postgres.

Usage:
    python -m app.search "what causes bitcoin price volatility"
    python -m app.search "regulatory risk" --source input/book.pdf --top-k 3
"""
import argparse

from app.db import SessionLocal, similarity_search
from app.embeddings import embed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--source", default=None, help="restrict to one source_file")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    query_vector = embed(args.query)

    session = SessionLocal()
    try:
        results = similarity_search(
            session, query_vector, top_k=args.top_k, source_file=args.source
        )
        for i, r in enumerate(results, 1):
            snippet = r.text.strip().replace("\n", " ")[:200]
            print(f"{i}. [page {r.page_number}, chunk {r.chunk_id}] {r.source_file}")
            print(f"   {snippet}...\n")
    finally:
        session.close()


if __name__ == "__main__":
    main()
