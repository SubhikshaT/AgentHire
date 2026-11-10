"""Evidence retrieval over resume chunks.

VECTOR_BACKEND=pgvector -> similarity computed in PostgreSQL (cosine distance operator)
VECTOR_BACKEND=python   -> chunks loaded and scored with NumPy
Both return the same structure.
"""
import uuid

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import ResumeChunk


def top_chunks(db: Session, resume_id: uuid.UUID, query_vec, k: int = 3, sections: list[str] | None = None) -> list[dict]:
    if query_vec is None:
        return []
    q = np.asarray(query_vec, dtype=np.float32)
    if not np.any(q):
        return []
    base = select(ResumeChunk).where(ResumeChunk.resume_id == resume_id, ResumeChunk.embedding.is_not(None))
    if sections:
        base = base.where(ResumeChunk.section.in_(sections))

    if get_settings().vector_backend == "pgvector":
        dist = ResumeChunk.embedding.cosine_distance(q.tolist())
        rows = db.execute(base.add_columns(dist.label("d")).order_by(dist).limit(k)).all()
        return [
            {"chunk_id": str(c.id), "section": c.section, "text": c.chunk_text, "similarity": round(1 - float(d), 4)}
            for c, d in rows
        ]

    chunks = db.scalars(base).all()
    if not chunks:
        return []
    mat = np.asarray([c.embedding for c in chunks], dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1) * (np.linalg.norm(q) or 1.0)
    sims = mat @ q / np.where(norms == 0, 1, norms)
    order = np.argsort(-sims)[:k]
    return [
        {"chunk_id": str(chunks[i].id), "section": chunks[i].section, "text": chunks[i].chunk_text,
         "similarity": round(float(sims[i]), 4)}
        for i in order
    ]
