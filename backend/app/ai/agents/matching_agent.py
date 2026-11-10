"""Candidate Matching Agent - hybrid, explainable score.

Pure function of plain inputs (no DB), so the same code is used by the API and
by scripts/evaluate_matching.py.

overall = 100 * sum(weight_i * component_i) / sum(weights)       (each component in 0..1)

Components (see docs/ai_methodology.md):
  semantic        cosine(job requirements text, candidate profile text), mapped [0.20, 0.80] -> [0, 1]
  required        mean over required skills: exact/synonym 1.0, related 0.5, missing 0
  preferred       same, over preferred skills (1.0 if the job lists none)
  experience      1.0 if no minimum; min(years / required, 1); 0.5 if years unknown
  education       1.0 level+field match, 0.5 level only, 0 otherwise (1.0 if job has no requirement)
  certification   share of job-listed certifications found (1.0 if the job lists none)
No personal identifiers (name, email, phone, photo, address) are used anywhere.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.ai.embeddings.model import cosine
from app.ai.taxonomy import get_taxonomy, normalize_text

DEFAULT_WEIGHTS = {
    "semantic": 35.0,
    "required_skills": 30.0,
    "preferred_skills": 10.0,
    "experience": 15.0,
    "education": 5.0,
    "certifications": 5.0,
}
SEMANTIC_LOW, SEMANTIC_HIGH = 0.20, 0.80
RELATED_CREDIT = 0.5
EDU_RANK = {"secondary": 1, "higher_secondary": 2, "diploma": 3, "bachelors": 4, "masters": 5, "phd": 6}
GENERIC_FIELDS = {"related field", "engineering"}
FIELD_FAMILIES = [
    {"computer science", "computer engineering", "information technology", "software engineering",
     "computer applications", "computer science and engineering", "information systems",
     "artificial intelligence", "data science", "artificial intelligence and data science"},
    {"electronics", "electrical", "electronics and communication"},
    {"mathematics", "statistics", "data science"},
]


def validate_weights(w: dict) -> dict:
    missing = set(DEFAULT_WEIGHTS) - set(w)
    extra = set(w) - set(DEFAULT_WEIGHTS)
    if missing or extra:
        raise ValueError(f"Weights must have exactly these keys: {sorted(DEFAULT_WEIGHTS)}")
    vals = {k: float(v) for k, v in w.items()}
    if any(v < 0 or v > 100 for v in vals.values()):
        raise ValueError("Each weight must be between 0 and 100.")
    if abs(sum(vals.values()) - 100) > 0.01:
        raise ValueError(f"Weights must add up to 100 (they add up to {sum(vals.values()):g}).")
    return vals


@dataclass
class CandidateSkillIn:
    key: str            # taxonomy key or normalized custom name
    name: str
    evidence_text: str | None = None
    evidence_section: str | None = None
    verified: bool = False


@dataclass
class CandidateIn:
    skills: list[CandidateSkillIn]
    total_experience_years: float | None
    education: list[dict]
    certifications: list[dict]
    profile_text: str           # summary + skills + experience + projects (no personal identifiers)
    raw_text: str = ""          # full resume text, for the keyword baseline only
    profile_embedding: list[float] | None = None


@dataclass
class JobIn:
    title: str
    required_skills: list[str]
    preferred_skills: list[str]
    minimum_experience: float | None
    education_requirements: list[dict]
    certifications: list[str]
    requirements_text: str
    embedding: list[float] | None = None


@dataclass
class MatchResult:
    components: dict[str, float]
    overall: float
    keyword_baseline: float
    explanation: dict = field(default_factory=dict)


def build_profile_text(summary: str | None, skill_names: list[str], work: list[dict], projects: list[dict],
                       education: list[dict]) -> str:
    """Text used for the candidate's semantic embedding. Personal identifiers are left out."""
    parts = []
    if summary:
        parts.append(summary)
    if skill_names:
        parts.append("Skills: " + ", ".join(skill_names))
    for e in work or []:
        parts.append(" ".join(x for x in [e.get("title"), e.get("description")] if x))
    for pr in projects or []:
        parts.append(" ".join(x for x in [pr.get("name"), pr.get("description")] if x))
    for ed in education or []:
        parts.append(" ".join(x for x in [ed.get("degree"), ed.get("field")] if x))
    return "\n".join(parts)[:6000]


def map_semantic(raw: float) -> float:
    return max(0.0, min(1.0, (raw - SEMANTIC_LOW) / (SEMANTIC_HIGH - SEMANTIC_LOW)))


def _skill_key(name: str) -> str:
    return get_taxonomy().resolve(name) or normalize_text(name)


def skill_coverage(job_skills: list[str], cand: dict[str, CandidateSkillIn]) -> tuple[float | None, list[dict], list[dict], list[str]]:
    """Returns (score or None if job lists none, matched, related, missing)."""
    tax = get_taxonomy()
    if not job_skills:
        return None, [], [], []
    matched, related, missing = [], [], []
    total = 0.0
    for name in job_skills:
        key = _skill_key(name)
        if key in cand:
            c = cand[key]
            matched.append({"skill": name, "key": key, "candidate_skill": c.name, "credit": 1.0,
                            "evidence_text": c.evidence_text, "evidence_section": c.evidence_section,
                            "verified": c.verified})
            total += 1.0
            continue
        rel = [c for ck, c in cand.items() if tax.are_related(key, ck)]
        if rel:
            cat = tax.skills[key].category if key in tax.skills else None
            best = sorted(rel, key=lambda c: (
                (tax.skills[c.key].category if c.key in tax.skills else None) != cat,  # same kind of skill first
                c.evidence_section != "skills", c.name))[0]
            related.append({"skill": name, "key": key, "candidate_skill": best.name, "credit": RELATED_CREDIT,
                            "note": f"Has {best.name}, which is related to {name} but not the same skill.",
                            "evidence_text": best.evidence_text, "evidence_section": best.evidence_section})
            total += RELATED_CREDIT
        else:
            missing.append(name)
    return total / len(job_skills), matched, related, missing


def education_score(reqs: list[dict], edu: list[dict]) -> tuple[float, str]:
    if not reqs:
        return 1.0, "The job lists no education requirement."
    req = reqs[0]
    need = EDU_RANK.get(req.get("level"), 0)
    fields = [f.lower() for f in req.get("fields", []) if f.lower() not in GENERIC_FIELDS]
    best_level_ok = False
    for e in edu:
        lvl = EDU_RANK.get(e.get("level") or "", 0)
        if lvl >= need:
            best_level_ok = True
            cf = (e.get("field") or e.get("degree") or "").lower()
            if not fields:
                return 1.0, f"Meets the {req.get('level')} requirement."
            if any(f in cf for f in fields) or any(
                    any(f in fam for f in fields) and any(x in cf for x in fam) for fam in FIELD_FAMILIES):
                return 1.0, f"Meets the {req.get('level')} requirement in a matching field."
    if best_level_ok:
        return 0.5, f"Meets the {req.get('level')} level, but the field does not clearly match."
    if not edu:
        return 0.0, "No education found in the resume."
    return 0.0, f"Does not show the required {req.get('level')} level."


def _cert_tokens(s: str) -> set[str]:
    stop = {"certified", "certification", "certificate", "is", "a", "plus", "the", "of", "in", "and", "or",
            "preferred", "required", "any", "relevant"}
    return {t for t in re.findall(r"[a-z0-9+#]+", s.lower()) if t not in stop and len(t) > 1}


def certification_score(job_certs: list[str], cand_certs: list[dict]) -> tuple[float, list[str], list[str]]:
    if not job_certs:
        return 1.0, [], []
    tax = get_taxonomy()
    cand_names = [c.get("name", "") for c in cand_certs]
    found, missing = [], []
    for jc in job_certs:
        jkeys = {k for k, _, _ in tax.find_in_text(jc, allow_ambiguous=True)}
        jt = _cert_tokens(jc)
        hit = None
        for cn in cand_names:
            ckeys = {k for k, _, _ in tax.find_in_text(cn, allow_ambiguous=True)}
            ct = _cert_tokens(cn)
            if (jkeys and jkeys & ckeys) or (jt and len(jt & ct) / len(jt) >= 0.5):
                hit = cn
                break
        (found if hit else missing).append(f"{jc} → {hit}" if hit else jc)
    return len(found) / len(job_certs), found, missing


def keyword_baseline(job: JobIn, raw_text: str) -> float:
    """Classic ATS baseline: share of job skill names that literally appear in the resume text."""
    names = job.required_skills + job.preferred_skills
    if not names:
        return 0.0
    low = raw_text.lower()
    hits = sum(1 for n in names if re.search(rf"(?<![a-z0-9]){re.escape(n.lower())}(?![a-z0-9])", low))
    return round(100.0 * hits / len(names), 1)


def score(job: JobIn, cand: CandidateIn, weights: dict | None = None) -> MatchResult:
    w = validate_weights(weights or DEFAULT_WEIGHTS)
    skills = {s.key: s for s in cand.skills}

    raw_sem = cosine(job.embedding, cand.profile_embedding) if job.embedding is not None and cand.profile_embedding is not None else 0.0
    sem = map_semantic(raw_sem)

    req, req_matched, req_related, req_missing = skill_coverage(job.required_skills, skills)
    pref, pref_matched, pref_related, pref_missing = skill_coverage(job.preferred_skills, skills)
    req = 0.0 if req is None else req
    pref = 1.0 if pref is None else pref

    yrs = cand.total_experience_years
    if not job.minimum_experience:
        exp, exp_note = 1.0, "The job has no minimum experience."
    elif yrs is None:
        exp, exp_note = 0.5, "Experience not stated in the resume (half credit, please verify)."
    else:
        exp = min(yrs / job.minimum_experience, 1.0)
        exp_note = (f"{yrs:g} years vs {job.minimum_experience:g} required." if exp >= 1
                    else f"{yrs:g} years vs {job.minimum_experience:g} required (gap of {job.minimum_experience - yrs:.1f} years).")

    edu, edu_note = education_score(job.education_requirements, cand.education)
    cert, cert_found, cert_missing = certification_score(job.certifications, cand.certifications)

    comps = {"semantic": sem, "required_skills": req, "preferred_skills": pref,
             "experience": exp, "education": edu, "certifications": cert}
    total_w = sum(w.values())
    overall = round(100.0 * sum(w[k] * comps[k] for k in comps) / total_w, 1)

    breakdown = [
        {"component": k, "raw_value": round(v, 4), "weight": w[k],
         "contribution": round(100.0 * w[k] * v / total_w, 2)}
        for k, v in comps.items()
    ]
    strengths = [f"{m['skill']} (required) — found in {m['evidence_section'] or 'profile'}" for m in req_matched]
    strengths += [f"{m['skill']} (preferred) — found in {m['evidence_section'] or 'profile'}" for m in pref_matched]
    if exp >= 1 and job.minimum_experience:
        strengths.append(f"Experience meets the minimum ({exp_note})")
    if edu == 1.0 and job.education_requirements:
        strengths.append(edu_note)
    gaps = [f"No evidence of {s} (required)" for s in req_missing]
    gaps += [f"{r['skill']}: only related skill {r['candidate_skill']} (not equivalent)" for r in req_related]
    gaps += [f"No evidence of {s} (preferred)" for s in pref_missing]
    if exp < 1:
        gaps.append(exp_note)
    if edu < 1:
        gaps.append(edu_note)
    gaps += [f"Certification not found: {c}" for c in cert_missing]
    unverified = [m["skill"] for m in req_matched + pref_matched if not m.get("verified")]

    explanation = {
        "breakdown": breakdown,
        "semantic": {"raw_cosine": round(raw_sem, 4), "mapped": round(sem, 4),
                     "mapping": f"linear [{SEMANTIC_LOW}, {SEMANTIC_HIGH}] -> [0, 1], clamped",
                     "note": "Cosine similarity of text embeddings. Not a probability."},
        "required_skills": {"matched": req_matched, "related": req_related, "missing": req_missing},
        "preferred_skills": {"matched": pref_matched, "related": pref_related, "missing": pref_missing},
        "experience": {"candidate_years": yrs, "required_years": job.minimum_experience, "note": exp_note},
        "education": {"note": edu_note, "requirements": job.education_requirements},
        "certifications": {"found": cert_found, "missing": cert_missing},
        "strengths": strengths,
        "gaps": gaps,
        "unverified_skills": unverified,
        "keyword_baseline": keyword_baseline(job, cand.raw_text),
        "disclaimer": "This score measures how well the resume evidence matches the job requirements. "
                      "It is not a probability of being hired or of job success.",
    }
    return MatchResult(components=comps, overall=overall, keyword_baseline=explanation["keyword_baseline"],
                       explanation=explanation)
