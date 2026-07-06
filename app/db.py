"""
Postgres + pgvector persistence layer.

Table `page_chunks` stores one row per PDF page (or you can store one
row per 20-page chunk instead — see note in tasks.py) along with an
embedding vector, so you can do semantic search over the whole book:

    SELECT text, page_number, source_file
    FROM page_chunks
    ORDER BY embedding <=> :query_embedding
    LIMIT 5;

`<=>` is pgvector's cosine-distance operator.
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, text
from sqlalchemy.orm import declarative_base, sessionmaker
from pgvector.sqlalchemy import Vector

from app.config import DATABASE_URL, EMBEDDING_DIM

Base = declarative_base()
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


class PageChunk(Base):
    __tablename__ = "page_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_file = Column(String, nullable=False, index=True)
    chunk_id = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=False)
    word_count = Column(Integer, default=0)
    text = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM))


def init_db():
    """Creates the pgvector extension (if missing) and all tables."""
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)


def save_page(session, source_file: str, chunk_id: int, page_number: int,
              text_content: str, word_count: int, embedding: list[float]):
    row = PageChunk(
        source_file=source_file,
        chunk_id=chunk_id,
        page_number=page_number,
        word_count=word_count,
        text=text_content,
        embedding=embedding,
    )
    session.add(row)
    return row


def similarity_search(session, query_embedding: list[float], top_k: int = 5,
                       source_file: str | None = None):
    """Returns the top_k most semantically similar pages (cosine distance)."""
    q = session.query(PageChunk)
    if source_file:
        q = q.filter(PageChunk.source_file == source_file)
    q = q.order_by(PageChunk.embedding.cosine_distance(query_embedding)).limit(top_k)
    return q.all()


if __name__ == "__main__":
    init_db()
    print("pgvector schema ready.")
