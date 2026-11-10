"""Interview Evaluation Agent.

Input : question, expected concepts, rubric, candidate answer (untrusted), rubric weights
Output: AnswerEvaluation (validated) + weighted score computed HERE (not by the LLM)

- concept_coverage(): deterministic check of which expected concepts appear in the answer.
  Always computed. Shown as a "basic concept coverage check" - never as a score.
- evaluate_with_llm(): rubric scoring by the LLM. Evidence quotes must be exact substrings
  of the answer; quotes that are not are dropped (hallucination guard).
- Empty / near-empty answers are marked 'insufficient' by rule (no LLM needed, nothing invented).
"""
from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

from app.ai.providers.base import LLMProvider, wrap_untrusted
from app.ai.rubric import DIMENSION_DESCRIPTIONS, VERDICTS, weighted_answer_score
from app.ai.taxonomy import get_taxonomy

PROMPT_VERSION = "eval-1.0"
MIN_WORDS = 5
STOP = {"the", "a", "an", "of", "and", "or", "to", "in", "on", "for", "with", "vs", "is", "are", "be", "it",
        "its", "as", "by", "at", "like", "using", "use", "when", "what", "how", "why", "your", "you", "each"}


class DimensionScores(BaseModel):
    technical_correctness: float = Field(ge=0, le=10)
    conceptual_understanding: float = Field(ge=0, le=10)
    problem_solving: float = Field(ge=0, le=10)
    clarity: float = Field(ge=0, le=10)
    relevance: float = Field(ge=0, le=10)


class AnswerEvaluation(BaseModel):
    scores: DimensionScores
    verdict: str
    strengths: list[str] = Field(default_factory=list, max_length=6)
    weaknesses: list[str] = Field(default_factory=list, max_length=6)
    missing_concepts: list[str] = Field(default_factory=list, max_length=8)
    explanation: str = Field(max_length=1500)
    suggested_improvement: str = Field(default="", max_length=800)
    evidence_quotes: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("verdict")
    @classmethod
    def valid_verdict(cls, v: str) -> str:
        v = v.strip().lower().replace(" ", "_").replace("-", "_")
        if v not in VERDICTS:
            raise ValueError(f"verdict must be one of {VERDICTS}")
        return v

    @field_validator("strengths", "weaknesses", "missing_concepts", "evidence_quotes")
    @classmethod
    def trim(cls, v: list[str]) -> list[str]:
        return [s.strip()[:300] for s in v if s and s.strip()]


def _tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9+#]+", s.lower()) if t not in STOP and len(t) > 1}


def _stem(t: str) -> str:
    for suf in ("ing", "ies", "es", "ed", "s"):
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            return t[: -len(suf)]
    return t


def concept_coverage(answer: str, concepts: list[str]) -> dict:
    """Detect expected concepts using keywords and common synonyms."""
    tax = get_taxonomy()
    ans_tokens = {_stem(t) for t in _tokens(answer)}
    ans_skills = {k for k, _, _ in tax.find_in_text(answer, allow_ambiguous=True)}
    answer_lower = answer.lower()

    aliases = {
        "non-blocking io": [
            "doesn't block", "does not block", "without blocking",
            "other tasks can run", "while waiting",
        ],
        "coroutines or promises": [
            "coroutine", "coroutines", "promise", "promises",
            "asynchronous function", "async function",
        ],
        "when it helps": [
            "api calls", "database queries", "network requests",
            "file operations", "io operations", "time-consuming tasks",
            "waiting for a response",
        ],
    }

    covered, missing = [], []

    for c in concepts:
        ct = {_stem(t) for t in _tokens(c)}
        ckeys = {k for k, _, _ in tax.find_in_text(c, allow_ambiguous=True)}

        alias_match = any(
            phrase in answer_lower
            for phrase in aliases.get(c.lower().strip(), [])
        )

        hit = (
            alias_match
            or bool(ckeys & ans_skills)
            or (bool(ct) and len(ct & ans_tokens) / len(ct) >= 0.5)
        )

        (covered if hit else missing).append(c)

    return {
        "covered": covered,
        "missing": missing,
        "note": "Basic keyword and synonym check. It does not verify correctness."
    }


def is_insufficient(answer: str | None) -> bool:
    return not answer or len(answer.split()) < MIN_WORDS


def insufficient_result(answer: str | None, concepts: list[str]) -> AnswerEvaluation:
    zero = DimensionScores(technical_correctness=0, conceptual_understanding=0, problem_solving=0, clarity=0,
                           relevance=0)
    return AnswerEvaluation(
        scores=zero, verdict="insufficient", strengths=[], weaknesses=["The answer is empty or too short to assess."],
        missing_concepts=list(concepts),
        explanation=("No answer was submitted." if not answer else
                     f"The answer has fewer than {MIN_WORDS} words, so there is not enough information to assess it."),
        suggested_improvement="Explain your approach in a few sentences and mention the key ideas.",
        evidence_quotes=[])


def evaluate_with_rules(
    question: str,
    answer: str,
    concepts: list[str]
) -> AnswerEvaluation:
    """Rule-based evaluation using concept coverage and question relevance."""

    coverage = concept_coverage(answer, concepts)
    covered = coverage["covered"]
    missing = coverage["missing"]

    question_tokens = {_stem(t) for t in _tokens(question)}
    answer_tokens = {_stem(t) for t in _tokens(answer)}

    overlap = len(question_tokens & answer_tokens)
    relevance_ratio = overlap / len(question_tokens) if question_tokens else 0

    coverage_ratio = len(covered) / len(concepts) if concepts else 0

    unrelated = relevance_ratio < 0.20 and coverage_ratio < 0.50

    if unrelated:
        score = 0.0
        verdict = "incorrect"
        explanation = (
            "The answer appears unrelated to the interview question. "
            "The question and answer share very few meaningful keywords, "
            "and expected concept coverage is low."
        )
        weaknesses = ["The answer does not sufficiently address the question."]
        strengths = []
    else:
        score = round(coverage_ratio * 10, 1) if concepts else 5.0

        if score >= 8:
            verdict = "correct"
        elif score >= 4:
            verdict = "partially_correct"
        else:
            verdict = "incorrect"

        explanation = (
            f"Basic rule-based assessment: {len(covered)} of "
            f"{len(concepts)} expected concepts were detected. "
            "This checks keyword coverage and question relevance, "
            "not factual correctness."
        )

        strengths = [f"Covered expected concept: {c}" for c in covered[:6]]
        weaknesses = [f"Expected concept not detected: {c}" for c in missing[:6]]

    scores = DimensionScores(
        technical_correctness=score,
        conceptual_understanding=score,
        problem_solving=score,
        clarity=score,
        relevance=0.0 if unrelated else round(relevance_ratio * 10, 1),
    )

    return AnswerEvaluation(
        scores=scores,
        verdict=verdict,
        strengths=strengths,
        weaknesses=weaknesses,
        missing_concepts=missing[:8],
        explanation=explanation,
        suggested_improvement=(
            "Answer the actual interview question and explain its key concepts."
            if unrelated else
            "Address the missing expected concepts and explain how they relate to the question."
            if missing else
            "Explain your reasoning and support your answer with an example."
        ),
        evidence_quotes=[],
    )

def evaluate_with_llm(provider: LLMProvider, question: str, concepts: list[str], rubric: list[str], answer: str,
                      difficulty: str, timeout: float):
    dims = "\n".join(f"- {k}: {v}" for k, v in DIMENSION_DESCRIPTIONS.items())
    system = (
        "You grade one interview answer against a rubric. Score each dimension from 0 to 10.\n"
        f"{dims}\n"
        "Verdict: 'correct' (accurate and complete enough), 'partially_correct' (some correct, important gaps), "
        "'incorrect' (main claims wrong), 'insufficient' (too little information to judge).\n"
        "Rules: do not reward length or confident tone; a long answer with wrong facts scores low. "
        "Judge only the answer text - do not assume knowledge that is not written. "
        "evidence_quotes must be copied EXACTLY from the answer. Do not judge personality, honesty or intelligence."
    )
    user = (
        f"Question ({difficulty}): {question}\nExpected concepts: {', '.join(concepts)}\n"
        f"Rubric:\n" + "\n".join(f"- {r}" for r in rubric) + "\n\n" + wrap_untrusted("candidate_answer", answer, 6000)
        + '\n\nReturn JSON: {"scores": {"technical_correctness", "conceptual_understanding", "problem_solving", '
          '"clarity", "relevance"}, "verdict", "strengths", "weaknesses", "missing_concepts", "explanation", '
          '"suggested_improvement", "evidence_quotes"}'
    )
    ev, meta = provider.generate_json(system, user, AnswerEvaluation, timeout)
    norm_answer = re.sub(r"\s+", " ", answer).lower()
    kept = [q for q in ev.evidence_quotes if re.sub(r"\s+", " ", q.strip(" \"'")).lower() in norm_answer]
    dropped = len(ev.evidence_quotes) - len(kept)
    ev.evidence_quotes = kept
    return ev, meta, dropped


def weighted(ev: AnswerEvaluation, weights: dict) -> float:
    return weighted_answer_score(ev.scores.model_dump(), weights)
