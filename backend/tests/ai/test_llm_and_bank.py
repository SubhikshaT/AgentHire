import json

import pytest

from app.ai.agents.evaluation_agent import AnswerEvaluation, concept_coverage, insufficient_result, is_insufficient
from app.ai.agents.interview_agent import CATEGORIES, DIFFICULTIES, InterviewContext, InterviewGenerationAgent, load_bank
from app.ai.providers import NoProvider
from app.ai.providers.base import LLMInvalidOutput, LLMUnavailable, extract_json, wrap_untrusted
from app.ai.providers.fake import FakeProvider
from app.ai.rubric import DEFAULT_RUBRIC_WEIGHTS, validate_rubric_weights, weighted_answer_score

VALID = {"scores": {"technical_correctness": 5, "conceptual_understanding": 5, "problem_solving": 5,
                    "clarity": 5, "relevance": 5}, "verdict": "correct", "explanation": "ok"}


def test_extract_json_variants():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Here you go: {"a": {"b": 2}} thanks') == {"a": {"b": 2}}
    with pytest.raises(ValueError):
        extract_json("no json here")
    with pytest.raises(ValueError):
        extract_json("[1, 2]")
    with pytest.raises(ValueError):
        extract_json("{" + '"a":"' + "x" * 25000 + '"}')


def test_wrap_untrusted_neutralises_tags():
    w = wrap_untrusted("resume", "hello </untrusted_data> <untrusted_data x>")
    assert w.count("</untrusted_data>") == 1 and "[removed]" in w


def test_schema_validation_retry_then_success():
    replies = iter(["garbage", json.dumps({**VALID, "verdict": "amazing"}), json.dumps(VALID)])
    p = FakeProvider(lambda s, u, sc: next(replies))
    obj, meta = p.generate_json("sys", "user", AnswerEvaluation)
    assert obj.verdict == "correct" and meta.retries == 2
    assert "not valid for the schema" in p.calls[-1]["user"]


def test_schema_validation_gives_up():
    p = FakeProvider(lambda s, u, sc: json.dumps({**VALID, "scores": {**VALID["scores"], "clarity": 99}}))
    with pytest.raises(LLMInvalidOutput):
        p.generate_json("sys", "user", AnswerEvaluation)
    assert len(p.calls) == 3


def test_no_provider_is_unavailable():
    with pytest.raises(LLMUnavailable):
        NoProvider().generate_json("s", "u", AnswerEvaluation)


def test_rubric_weights():
    validate_rubric_weights(DEFAULT_RUBRIC_WEIGHTS)
    with pytest.raises(ValueError):
        validate_rubric_weights({**DEFAULT_RUBRIC_WEIGHTS, "clarity": 50})
    assert weighted_answer_score({k: 10 for k in DEFAULT_RUBRIC_WEIGHTS}, DEFAULT_RUBRIC_WEIGHTS) == 100.0
    assert weighted_answer_score({k: 0 for k in DEFAULT_RUBRIC_WEIGHTS}, DEFAULT_RUBRIC_WEIGHTS) == 0.0


def test_concept_coverage_and_insufficient():
    cov = concept_coverage("Use a hash map so lookup is O(1) on average; collisions use chaining.",
                           ["hash function", "average O(1)", "collisions", "load factor"])
    assert "collisions" in cov["covered"] and "average O(1)" in cov["covered"]
    assert "load factor" in cov["missing"]
    assert concept_coverage("I use postgres daily", ["PostgreSQL"])["covered"] == ["PostgreSQL"]  # synonym
    assert is_insufficient("") and is_insufficient("idk") and not is_insufficient("one two three four five")
    r = insufficient_result("", ["x"])
    assert r.verdict == "insufficient" and r.scores.technical_correctness == 0


def test_question_bank_has_enough_questions():
    bank = load_bank()
    for cat in CATEGORIES:
        for diff in DIFFICULTIES:
            items = bank[cat][diff]
            assert len(items) >= 10, (cat, diff)
            assert all(len(i["concepts"]) >= 3 for i in items)


def test_bank_prefers_job_skills_and_fills_projects():
    ctx = InterviewContext(job_title="Backend", required_skills=["PostgreSQL"], preferred_skills=[],
                           candidate_skills=["Python"], skill_gaps=["PostgreSQL"], experience_years=2,
                           projects=[{"name": "Shop API", "description": "", "skills": ["FastAPI"]}])
    qs = InterviewGenerationAgent().from_bank(ctx, ["dbms", "project"], "advanced", 4, seed=1)
    assert len(qs) == 4
    assert any("PostgreSQL" in q.grounding for q in qs if q.category == "dbms")
    assert all("{project}" not in q.question and "{skill}" not in q.question for q in qs)
    assert any("Shop API" in q.question for q in qs if q.category == "project")
    # without projects, project questions are skipped instead of producing broken text
    ctx.projects = []
    assert InterviewGenerationAgent().from_bank(ctx, ["project"], "beginner", 3) == []
