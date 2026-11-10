"""Skill graph for one candidate vs one job. Edges come only from the curated taxonomy."""
import uuid
from collections import deque

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.taxonomy import get_taxonomy
from app.core.exceptions import NotFoundError
from app.models import Application, Job, User
from app.services.permissions import get_visible_candidate


def _path(start_keys: set[str], target: str, max_depth: int = 3) -> list[str] | None:
    """Shortest taxonomy path from any skill the candidate has to the target skill."""
    tax = get_taxonomy()
    if target not in tax.skills:
        return None
    q = deque([(k, [k]) for k in start_keys if k in tax.skills])
    seen = set(start_keys)
    while q:
        node, path = q.popleft()
        if len(path) > max_depth + 1:
            continue
        for nb in sorted(tax.skills[node].related):
            if nb == target:
                return path + [nb]
            if nb not in seen:
                seen.add(nb)
                q.append((nb, path + [nb]))
    return None


def build(db: Session, user: User, candidate_id: uuid.UUID, job_id: uuid.UUID) -> dict:
    tax = get_taxonomy()
    cand = get_visible_candidate(db, user, candidate_id)
    job = db.get(Job, job_id)
    if job is None or not db.scalar(select(Application.id).where(Application.job_id == job_id,
                                                                 Application.candidate_id == cand.id)):
        raise NotFoundError("This candidate has not applied to that job.")
    have = {cs.skill.normalized_name: cs.skill.name for cs in cand.skills}
    req = {tax.resolve(s) or s.lower(): s for s in job.required_skills or []}
    pref = {tax.resolve(s) or s.lower(): s for s in job.preferred_skills or []}

    nodes: dict[str, dict] = {}

    def add(key, label, kind, **extra):
        if key not in nodes:
            nodes[key] = {"id": key, "label": label, "kind": kind, **extra}

    for k, label in {**pref, **req}.items():
        importance = "required" if k in req else "preferred"
        if k in have:
            add(k, label, "matched", importance=importance)
        elif any(tax.are_related(k, h) for h in have):
            add(k, label, "related_only", importance=importance)
        else:
            add(k, label, "missing", importance=importance)
    for k, label in have.items():
        add(k, label, "candidate")

    edges = []
    keys = list(nodes)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if tax.are_related(a, b):
                kind = "transferable" if (nodes[a]["kind"] == "candidate" and nodes[b]["kind"] in ("related_only",)) or (
                    nodes[b]["kind"] == "candidate" and nodes[a]["kind"] in ("related_only",)) else "related"
                edges.append({"source": a, "target": b, "kind": kind})

    learning_paths = []
    for k, n in list(nodes.items()):
        if n["kind"] not in ("missing", "related_only"):
            continue
        p = _path(set(have), k)
        if p:
            for mid in p[1:-1]:
                add(mid, tax.display(mid), "path")
            for a, b in zip(p, p[1:]):
                if not any({e["source"], e["target"]} == {a, b} for e in edges):
                    edges.append({"source": a, "target": b, "kind": "path"})
            learning_paths.append({"target": n["label"], "path": [tax.display(x) for x in p]})
        else:
            learning_paths.append({"target": n["label"], "path": None})
    return {"candidate_id": cand.id, "job_id": job.id, "job_title": job.title, "nodes": list(nodes.values()),
            "edges": edges, "learning_paths": learning_paths,
            "note": "Links come only from the curated skill taxonomy (related skills). No link means no known relation."}
