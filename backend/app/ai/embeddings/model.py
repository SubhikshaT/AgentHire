"""Sentence-Transformers embedding model (loaded once, on first use, CPU)."""
import logging
import threading
import time

import numpy as np

from app.core.config import get_settings

logger = logging.getLogger("agenthire.embeddings")
_lock = threading.Lock()
_model = None


class EmbeddingError(Exception):
    pass


def model_name() -> str:
    return get_settings().embedding_model


def get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                try:
                    from sentence_transformers import SentenceTransformer

                    t = time.perf_counter()
                    _model = SentenceTransformer(model_name(), device="cpu")
                    logger.info("Loaded embedding model %s in %.1fs", model_name(), time.perf_counter() - t)
                except Exception as e:
                    raise EmbeddingError(f"Could not load embedding model '{model_name()}': {e}") from e
    return _model


def embed(texts: list[str]) -> np.ndarray:
    """Return L2-normalized embeddings, shape (n, dim). Empty texts become zero vectors."""
    if not texts:
        return np.zeros((0, get_settings().embedding_dim), dtype=np.float32)
    model = get_model()
    safe = [t if t and t.strip() else " " for t in texts]
    try:
        vecs = model.encode(safe, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
    except Exception as e:
        raise EmbeddingError(f"Embedding failed: {e}") from e
    vecs = np.asarray(vecs, dtype=np.float32)
    for i, t in enumerate(texts):
        if not t or not t.strip():
            vecs[i] = 0.0
    return vecs


def embed_one(text: str) -> list[float]:
    return embed([text])[0].tolist()


def cosine(a, b) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))
