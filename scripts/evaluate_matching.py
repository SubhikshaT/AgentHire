"""Evaluate the matching engine on the fixed synthetic test set.

Compares three rankers on 10 jobs x 30 candidates:
  1. keyword baseline  - share of job skill names literally present in the resume text
  2. semantic only     - raw cosine similarity of embeddings
  3. hybrid            - the AgentHire weighted score (default weights)

The same pipeline as the app is used: resumes are parsed by the Resume agent,
jobs by the Job agent. Labels come from sample_data/labels.json (rule-based, see README).
Relevant = label >= 2. NDCG uses graded gain (2^label - 1).

Usage (from the backend folder, venv active):
  python ../scripts/evaluate_matching.py                      # MiniLM only
  python ../scripts/evaluate_matching.py --compare-models     # also all-mpnet-base-v2 (bigger download)
Writes docs/matching_evaluation.md
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")

from app.ai.agents.job_agent import JobAnalysisAgent  # noqa: E402
from app.ai.agents.matching_agent import (  # noqa: E402
    CandidateIn,
    CandidateSkillIn,
    JobIn,
    build_profile_text,
    keyword_baseline,
    score,
)
from app.ai.agents.resume_agent import ResumeIntelligenceAgent  # noqa: E402
from app.ai.parsing.extract import extract_text  # noqa: E402
from app.services.job_service import job_text_for_embedding  # noqa: E402

def peak_rss_mb() -> float | None:
    """Peak memory of this process in MB (None if it cannot be measured on this OS)."""
    try:
        import resource  # Linux / macOS

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    except ImportError:
        try:
            import psutil  # optional on Windows

            return psutil.Process().memory_info().rss / (1024 * 1024)
        except ImportError:
            return None


K = 5
REL = 2


def precision_at_k(ranked, rel, k=K):
    return sum(1 for c in ranked[:k] if rel[c] >= REL) / k


def recall_at_k(ranked, rel, k=K):
    total = sum(1 for v in rel.values() if v >= REL)
    return (sum(1 for c in ranked[:k] if rel[c] >= REL) / total) if total else 0.0


def ndcg_at_k(ranked, rel, k=K):
    dcg = sum((2 ** rel[c] - 1) / math.log2(i + 2) for i, c in enumerate(ranked[:k]))
    ideal = sorted(rel.values(), reverse=True)[:k]
    idcg = sum((2 ** v - 1) / math.log2(i + 2) for i, v in enumerate(ideal))
    return dcg / idcg if idcg else 0.0


def mrr(ranked, rel):
    for i, c in enumerate(ranked):
        if rel[c] >= REL:
            return 1 / (i + 1)
    return 0.0


def load_data():
    jobs = json.loads((ROOT / "sample_data/synthetic_jobs/jobs.json").read_text())
    manifest = json.loads((ROOT / "sample_data/synthetic_candidates/manifest.json").read_text())
    labels = json.loads((ROOT / "sample_data/labels.json").read_text())["labels"]
    agent = ResumeIntelligenceAgent(today=date(2026, 10, 1))
    cands = {}
    for m in manifest:
        p = ROOT / "sample_data/synthetic_candidates" / m["file"]
        text, _ = extract_text(p.read_bytes(), p.suffix[1:])
        cands[m["id"]] = (agent.parse(text), text)
    janalysis = {}
    for j in jobs:
        a = JobAnalysisAgent().analyze(j["description"], j["title"])
        janalysis[j["id"]] = a
    return jobs, cands, janalysis, labels


def evaluate(model_name: str, jobs, cands, janalysis, labels):
    from sentence_transformers import SentenceTransformer

    rss0 = peak_rss_mb()
    t0 = time.perf_counter()
    model = SentenceTransformer(model_name, device="cpu")
    load_s = time.perf_counter() - t0

    cand_text = {cid: build_profile_text(p.professional_summary, [s.name for s in p.skills],
                                         [e.model_dump() for e in p.work_experience],
                                         [x.model_dump() for x in p.projects],
                                         [e.model_dump() for e in p.education]) for cid, (p, _) in cands.items()}
    job_ns = {}
    for j in jobs:
        a = janalysis[j["id"]]
        job_ns[j["id"]] = SimpleNamespace(title=j["title"], required_skills=a.required_skills,
                                          preferred_skills=a.preferred_skills, responsibilities=a.responsibilities,
                                          minimum_experience=a.minimum_experience, description=j["description"])
    texts = list(cand_text.values()) + [job_text_for_embedding(n) for n in job_ns.values()]
    t1 = time.perf_counter()
    vecs = model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
    enc_s = time.perf_counter() - t1
    cvec = dict(zip(cand_text, vecs[: len(cand_text)]))
    jvec = dict(zip(job_ns, vecs[len(cand_text):]))
    rss1 = peak_rss_mb()

    rankers = {"keyword": {}, "semantic": {}, "hybrid": {}}
    for j in jobs:
        a, jid = janalysis[j["id"]], j["id"]
        jin = JobIn(title=j["title"], required_skills=a.required_skills, preferred_skills=a.preferred_skills,
                    minimum_experience=a.minimum_experience, education_requirements=a.education_requirements,
                    certifications=a.certifications, requirements_text="", embedding=jvec[jid].tolist())
        rows = []
        for cid, (p, raw) in cands.items():
            cin = CandidateIn(
                skills=[CandidateSkillIn(key=s.key, name=s.name, evidence_text=s.evidence_text,
                                         evidence_section=s.evidence_section) for s in p.skills],
                total_experience_years=p.total_experience_years, education=[e.model_dump() for e in p.education],
                certifications=[c.model_dump() for c in p.certifications], profile_text=cand_text[cid],
                raw_text=raw, profile_embedding=cvec[cid].tolist())
            h = score(jin, cin)
            rows.append((cid, keyword_baseline(jin, raw), float(jvec[jid] @ cvec[cid]), h.overall))
        for name, idx in (("keyword", 1), ("semantic", 2), ("hybrid", 3)):
            # ties broken by candidate id so results are reproducible
            rankers[name][jid] = [r[0] for r in sorted(rows, key=lambda r: (-r[idx], r[0]))]

    results = {}
    for name, per_job in rankers.items():
        m = {"P@5": [], "R@5": [], "NDCG@5": [], "MRR": []}
        for jid, ranked in per_job.items():
            rel = labels[jid]
            m["P@5"].append(precision_at_k(ranked, rel))
            m["R@5"].append(recall_at_k(ranked, rel))
            m["NDCG@5"].append(ndcg_at_k(ranked, rel))
            m["MRR"].append(mrr(ranked, rel))
        results[name] = {k: sum(v) / len(v) for k, v in m.items()}
    perf = {"load_s": load_s, "encode_s": enc_s, "texts": len(texts),
            "ms_per_text": 1000 * enc_s / len(texts),
            "rss_increase_mb": (rss1 - rss0) if rss0 is not None and rss1 is not None else None}
    return results, perf, rankers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare-models", action="store_true")
    args = ap.parse_args()
    jobs, cands, janalysis, labels = load_data()
    models = ["sentence-transformers/all-MiniLM-L6-v2"]
    if args.compare_models:
        models.append("sentence-transformers/all-mpnet-base-v2")
    all_res = {}
    for m in models:
        print(f"Evaluating with {m} ...")
        all_res[m] = evaluate(m, jobs, cands, janalysis, labels)

    n_rel = sum(1 for j in labels.values() for v in j.values() if v >= REL)
    lines = [
        "# Matching evaluation", "",
        f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M')} · script: `scripts/evaluate_matching.py`", "",
        "## Test set",
        f"- {len(jobs)} synthetic jobs × {len(cands)} synthetic resumes ({len(jobs) * len(cands)} pairs).",
        f"- Labels 0–3 from the written rule in `sample_data/README.md` (archetype + years). "
        f"Relevant = label ≥ {REL}: {n_rel} relevant pairs.",
        "- Resumes and jobs go through the same parsing/analysis code as the app. Default weights.",
        f"- Metrics at K = {K}, averaged over the 10 jobs.", "",
    ]
    for m, (res, perf, _) in all_res.items():
        lines += [f"## Results — `{m}`", "", "| Ranker | P@5 | R@5 | NDCG@5 | MRR |", "|---|---:|---:|---:|---:|"]
        for name in ("keyword", "semantic", "hybrid"):
            r = res[name]
            label = {"keyword": "Keyword baseline", "semantic": "Semantic only", "hybrid": "Hybrid (AgentHire)"}[name]
            lines.append(f"| {label} | {r['P@5']:.3f} | {r['R@5']:.3f} | {r['NDCG@5']:.3f} | {r['MRR']:.3f} |")
        lines += ["", f"Model load {perf['load_s']:.1f} s · encoding {perf['texts']} texts in {perf['encode_s']:.2f} s "
                      f"({perf['ms_per_text']:.1f} ms/text, CPU) · peak memory increase ≈ "
                      + (f"{perf['rss_increase_mb']:.0f} MB" if perf['rss_increase_mb'] is not None else "n/a"), ""]
    if len(all_res) > 1:
        lines += ["## Model choice",
                  "AgentHire keeps **all-MiniLM-L6-v2** as the default: on this set the hybrid score is about the same "
                  "with either model, while MiniLM loads and encodes several times faster and uses less memory on a "
                  "normal laptop CPU. mpnet helps the *semantic-only* ranking more, so it is worth trying if you rely "
                  "on semantic search alone (set EMBEDDING_MODEL in .env; embedding size changes to 768, which needs a "
                  "new migration for the pgvector column).", ""]
    lines += [
        "## How to read this",
        "- These numbers are measured on a small, synthetic, rule-labelled set. They show how the rankers "
        "compare on this set; they are not a claim about accuracy on real hiring data.",
        "- Some labels are deliberately hard: e.g. an iOS developer is labelled relevant for the Android job "
        "because the label rule only uses role family and years, not exact skills.",
        "- Recall@5 is capped when a job has more than 5 relevant candidates.",
    ]
    out = ROOT / "docs/matching_evaluation.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
