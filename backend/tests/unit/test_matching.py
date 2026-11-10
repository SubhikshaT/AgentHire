import pytest

from app.ai.agents.matching_agent import (
    DEFAULT_WEIGHTS,
    CandidateIn,
    CandidateSkillIn,
    JobIn,
    certification_score,
    education_score,
    keyword_baseline,
    map_semantic,
    score,
    skill_coverage,
    validate_weights,
)


def cand(keys, years=3.0, edu=None, certs=None, text="python developer"):
    return CandidateIn(
        skills=[CandidateSkillIn(key=k, name=k, evidence_text=f"used {k}", evidence_section="skills") for k in keys],
        total_experience_years=years, education=edu or [], certifications=certs or [],
        profile_text=text, raw_text=text, profile_embedding=None)


def job(req, pref=(), min_exp=2.0, edu=None, certs=()):
    return JobIn(title="Backend", required_skills=list(req), preferred_skills=list(pref), minimum_experience=min_exp,
                 education_requirements=edu or [], certifications=list(certs), requirements_text="", embedding=None)


def test_semantic_mapping_is_clamped_linear():
    assert map_semantic(0.1) == 0.0
    assert map_semantic(0.2) == 0.0
    assert map_semantic(0.5) == pytest.approx(0.5)
    assert map_semantic(0.9) == 1.0


def test_required_skill_coverage_exact_synonym_related_missing():
    c = {k: CandidateSkillIn(key=k, name=k) for k in ["python", "django", "postgresql"]}
    s, matched, related, missing = skill_coverage(["Python", "FastAPI", "Postgres", "Kubernetes"], c)
    assert [m["skill"] for m in matched] == ["Python", "Postgres"]   # synonym = full credit
    assert related[0]["skill"] == "FastAPI" and related[0]["candidate_skill"] == "django"
    assert "not the same skill" in related[0]["note"]
    assert missing == ["Kubernetes"]
    assert s == pytest.approx((1 + 0.5 + 1 + 0) / 4)


def test_prompt_example_django_is_related_not_equal_to_fastapi():
    r = score(job(["Python", "FastAPI", "PostgreSQL", "REST APIs"]),
              cand(["python", "django", "postgresql", "backend_development"]))
    ex = r.explanation["required_skills"]
    assert {m["skill"] for m in ex["matched"]} == {"Python", "PostgreSQL"}
    rel = {x["skill"]: x["candidate_skill"] for x in ex["related"]}
    assert rel["FastAPI"] == "django"
    assert "REST APIs" in rel   # backend development is related to REST APIs
    assert ex["missing"] == []
    assert any("FastAPI: only related skill" in g for g in r.explanation["gaps"])


def test_experience_component():
    assert score(job(["Python"], min_exp=4), cand(["python"], years=2)).components["experience"] == 0.5
    assert score(job(["Python"], min_exp=4), cand(["python"], years=9)).components["experience"] == 1.0
    assert score(job(["Python"], min_exp=0), cand(["python"], years=0)).components["experience"] == 1.0
    r = score(job(["Python"], min_exp=2), cand(["python"], years=None))
    assert r.components["experience"] == 0.5 and "not stated" in r.explanation["experience"]["note"]


def test_education_component():
    req = [{"level": "bachelors", "fields": ["computer science", "related field"]}]
    assert education_score(req, [{"level": "bachelors", "field": "Computer Science and Engineering"}])[0] == 1.0
    assert education_score(req, [{"level": "masters", "field": "Information Technology"}])[0] == 1.0
    assert education_score(req, [{"level": "bachelors", "field": "Mechanical"}])[0] == 0.5
    assert education_score(req, [{"level": "diploma", "field": "Computer Science"}])[0] == 0.0
    assert education_score([], [])[0] == 1.0


def test_certification_component():
    s, found, missing = certification_score(["AWS certification preferred"], [{"name": "AWS Certified Cloud Practitioner"}])
    assert s == 1.0 and found
    s, _, missing = certification_score(["CKA Kubernetes certification"], [{"name": "Oracle Java SE"}])
    assert s == 0.0 and missing
    assert certification_score([], [])[0] == 1.0


def test_overall_is_weighted_and_traceable():
    r = score(job(["Python", "Docker"], pref=["Redis"], min_exp=2), cand(["python"], years=1))
    total = sum(b["contribution"] for b in r.explanation["breakdown"])
    assert r.overall == pytest.approx(total, abs=0.05)
    assert 0 <= r.overall <= 100
    # with semantic weight 0 and no embedding, the score is fully determined by structured parts
    w = {**DEFAULT_WEIGHTS, "semantic": 0, "required_skills": 65}
    r2 = score(job(["Python", "Docker"], min_exp=2), cand(["python"], years=2), w)
    assert r2.overall == pytest.approx(100 * (65 * 0.5 + 10 * 1 + 15 * 1 + 5 + 5) / 100, abs=0.05)


def test_weights_validation():
    validate_weights(DEFAULT_WEIGHTS)
    with pytest.raises(ValueError):
        validate_weights({**DEFAULT_WEIGHTS, "semantic": 50})
    with pytest.raises(ValueError):
        validate_weights({"semantic": 100})
    with pytest.raises(ValueError):
        validate_weights({**DEFAULT_WEIGHTS, "semantic": -5, "education": 45})


def test_keyword_baseline_has_no_synonyms():
    j = job(["PostgreSQL", "Python"])
    assert keyword_baseline(j, "I use postgres and python") == 50.0   # 'postgres' does not count
    assert keyword_baseline(j, "postgresql, python") == 100.0


def test_scoring_ignores_personal_identifiers():
    a = cand(["python"], text="Skills: Python")
    b = cand(["python"], text="Skills: Python")
    b.raw_text = "Name: Some Different Person, female, 45 years old\nSkills: Python"
    j = job(["Python"])
    assert score(j, a).overall == score(j, b).overall
