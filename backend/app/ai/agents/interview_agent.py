"""Interview Generation Agent.

Input : job requirements, candidate skills / gaps (no personal identifiers), retrieved resume
        project chunks (RAG), categories, difficulty, count
Output: list[GeneratedQuestion] (validated)

With an LLM: questions are generated and grounded in the job + resume chunks.
Without an LLM: questions are picked from the curated local bank (data/question_bank.json),
preferring ones tagged with the job's skills and the candidate's gaps.
"""
from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from app.ai.providers.base import LLMProvider, wrap_untrusted
from app.ai.taxonomy import get_taxonomy

PROMPT_VERSION = "qgen-1.0"
CATEGORIES = {
    "programming": "Programming", "dsa": "Data Structures and Algorithms", "dbms": "Database Management",
    "os": "Operating Systems", "networks": "Computer Networks", "software_engineering": "Software Engineering",
    "system_design": "System Design", "project": "Project-Based", "behavioral": "Behavioral",
}
DIFFICULTIES = ("beginner", "intermediate", "advanced")
BANK = Path(__file__).resolve().parents[1] / "data" / "question_bank.json"


class GeneratedQuestion(BaseModel):
    question: str = Field(min_length=10, max_length=600)
    category: str
    difficulty: str
    expected_concepts: list[str] = Field(min_length=1, max_length=8)
    evaluation_rubric: list[str] = Field(min_length=1, max_length=8)
    time_limit_seconds: int = Field(default=120, ge=30, le=900)
    source: str = "llm"
    grounding: str = Field(default="", max_length=400)

    @field_validator("category")
    @classmethod
    def valid_cat(cls, v: str) -> str:
        if v not in CATEGORIES:
            raise ValueError(f"category must be one of {list(CATEGORIES)}")
        return v

    @field_validator("difficulty")
    @classmethod
    def valid_diff(cls, v: str) -> str:
        if v not in DIFFICULTIES:
            raise ValueError("difficulty must be beginner, intermediate or advanced")
        return v

    @field_validator("expected_concepts", "evaluation_rubric")
    @classmethod
    def short_items(cls, v: list[str]) -> list[str]:
        return [s.strip()[:200] for s in v if s and s.strip()]


class QuestionSet(BaseModel):
    questions: list[GeneratedQuestion] = Field(min_length=1, max_length=15)


class FollowUp(BaseModel):
    question: str = Field(min_length=10, max_length=500)
    expected_concepts: list[str] = Field(min_length=1, max_length=6)


class InterviewContext(BaseModel):
    job_title: str
    required_skills: list[str]
    preferred_skills: list[str]
    candidate_skills: list[str]
    skill_gaps: list[str]
    experience_years: float | None
    projects: list[dict]                 # [{"name":..., "description":..., "skills":[...]}]
    project_chunks: list[str] = Field(default_factory=list)   # retrieved resume text (RAG)


def default_time_limit(category: str, difficulty: str) -> int:
    base = {"beginner": 120, "intermediate": 180, "advanced": 240}[difficulty]
    if category in ("system_design",):
        base += 120
    if category == "behavioral":
        base = 180
    return base


def rubric_from_concepts(concepts: list[str]) -> list[str]:
    lines = [f"Covers: {c}" for c in concepts[:5]]
    lines.append("Statements are technically correct (wrong facts lower the score)")
    lines.append("Explains clearly; length alone earns nothing")
    return lines


@lru_cache
def load_bank() -> dict:
    return json.loads(BANK.read_text(encoding="utf-8"))


class InterviewGenerationAgent:
    name = "interview_generation"

    # ------------------------------------------------------------- question bank
    def from_bank(self, ctx: InterviewContext, categories: list[str], difficulty: str, count: int,
                  seed: int | None = None) -> list[GeneratedQuestion]:
        tax = get_taxonomy()
        bank = load_bank()
        rnd = random.Random(seed)
        job_keys = {tax.resolve(s) or s.lower() for s in ctx.required_skills + ctx.preferred_skills}
        gap_keys = {tax.resolve(s) or s.lower() for s in ctx.skill_gaps}
        cand_keys = {tax.resolve(s) or s.lower() for s in ctx.candidate_skills}
        per_cat: dict[str, list[GeneratedQuestion]] = {}
        for cat in categories:
            pool = bank.get(cat, {}).get(difficulty, [])
            scored = []
            for item in pool:
                tags = set(item.get("skills", []))
                rel = 0.0
                if tags:
                    rel = 3 * len(tags & gap_keys) + 2 * len(tags & job_keys) + 1 * len(tags & cand_keys)
                    if rel == 0:
                        rel = -1.0  # tagged for unrelated skills: use only if nothing else
                scored.append((rel + rnd.random() * 0.5, item))
            scored.sort(key=lambda t: -t[0])
            qs = []
            for _, item in scored:
                q = self._fill(item, cat, difficulty, ctx, rnd)
                if q:
                    qs.append(q)
            per_cat[cat] = qs
        # round-robin across chosen categories so the mix is even
        out: list[GeneratedQuestion] = []
        seen: set[str] = set()
        while len(out) < count and any(per_cat.values()):
            for cat in categories:
                if per_cat.get(cat) and len(out) < count:
                    q = per_cat[cat].pop(0)
                    if q.question.lower() not in seen:
                        seen.add(q.question.lower())
                        out.append(q)
        return out

    def _fill(self, item: dict, cat: str, difficulty: str, ctx: InterviewContext, rnd: random.Random):
        text = item["q"]
        grounding = "Question bank"
        if "{project}" in text:
            if not ctx.projects:
                return None
            p = rnd.choice(ctx.projects)
            text = text.replace("{project}", p["name"])
            grounding = f"Resume project: {p['name']}"
            if "{skill}" in text:
                skills = p.get("skills") or ctx.candidate_skills
                if not skills:
                    return None
                text = text.replace("{skill}", rnd.choice(skills))
        tags = item.get("skills", [])
        if tags:
            tax = get_taxonomy()
            grounding = "Question bank · topic: " + ", ".join(tax.display(t) for t in tags[:3])
        return GeneratedQuestion(
            question=text, category=cat, difficulty=difficulty, expected_concepts=item["concepts"],
            evaluation_rubric=rubric_from_concepts(item["concepts"]),
            time_limit_seconds=default_time_limit(cat, difficulty), source="question_bank", grounding=grounding)

    # ------------------------------------------------------------- LLM
    def with_llm(self, provider: LLMProvider, ctx: InterviewContext, categories: list[str], difficulty: str,
                 count: int, timeout: float):
        cats = ", ".join(f"{c} ({CATEGORIES[c]})" for c in categories)
        system = (
            "You write technical interview questions for a recruiter. Questions must test skills needed for the job, "
            "probe the candidate's skill gaps, and may refer to the candidate's real projects given in the data. "
            "Never ask about age, gender, religion, family, nationality, health or other personal characteristics. "
            "Each question needs expected_concepts (what a good answer mentions) and an evaluation_rubric "
            "(short checklist lines). 'grounding' says which job requirement or resume project the question is based on."
        )
        user = (
            f"Write exactly {count} questions. Difficulty: {difficulty}. Use only these categories: {cats}. "
            f"Spread questions across the categories. Use the category keys exactly as given.\n\n"
            f"JOB: {ctx.job_title}\nRequired skills: {', '.join(ctx.required_skills)}\n"
            f"Preferred skills: {', '.join(ctx.preferred_skills)}\n"
            f"CANDIDATE skills: {', '.join(ctx.candidate_skills[:40])}\n"
            f"Skill gaps (missing or only related): {', '.join(ctx.skill_gaps) or 'none'}\n"
            f"Experience: {ctx.experience_years if ctx.experience_years is not None else 'not stated'} years\n"
            f"Projects: {', '.join(p['name'] for p in ctx.projects[:6]) or 'none'}\n\n"
            + wrap_untrusted("resume_projects", "\n---\n".join(ctx.project_chunks[:4]), 3000)
            + '\n\nReturn JSON: {"questions": [{"question", "category", "difficulty", "expected_concepts", '
              '"evaluation_rubric", "time_limit_seconds", "grounding"}]}'
        )
        result, meta = provider.generate_json(system, user, QuestionSet, timeout)
        qs, seen = [], set()
        for q in result.questions:
            if q.category not in categories or q.question.lower() in seen:
                continue
            seen.add(q.question.lower())
            q.difficulty = difficulty
            q.source = "llm"
            qs.append(q)
        return qs[:count], meta

    def follow_up(self, provider: LLMProvider, question: str, concepts: list[str], answer: str, missing: list[str],
                  timeout: float):
        system = ("You are a professional technical interviewer. Write ONE short follow-up question that gives the "
                  "candidate a fair chance to explain the missing concepts. Do not reveal the answer.")
        user = (f"Original question: {question}\nExpected concepts: {', '.join(concepts)}\n"
                f"Concepts not yet covered: {', '.join(missing)}\n\n" + wrap_untrusted("candidate_answer", answer, 4000)
                + '\n\nReturn JSON: {"question": "...", "expected_concepts": ["..."]}')
        return provider.generate_json(system, user, FollowUp, timeout)
