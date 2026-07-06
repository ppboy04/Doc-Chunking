"""
Generates embeddings locally with sentence-transformers (no API key,
no external calls once the model is cached in the image/volume).

Swap `embed()` for an OpenAI/Anthropic/Cohere embeddings call if you'd
rather use a hosted model — everything else (db.py, tasks.py) stays
the same as long as you also update EMBEDDING_DIM in config.py to
match the new model's output size.
"""
from functools import lru_cache

from app.config import EMBEDDING_MODEL


@lru_cache(maxsize=1)
def _get_model():
    # Imported lazily so `python -m app.chunker` etc. don't pay the
    # (heavy) import cost if they never need embeddings.
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL)


def embed(text: str) -> list[float]:
    if not text or not text.strip():
        # zero-vector for blank pages instead of erroring
        model = _get_model()
        return [0.0] * model.get_sentence_embedding_dimension()
    model = _get_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    return model.encode(texts, normalize_embeddings=True).tolist()
