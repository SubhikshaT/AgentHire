"""Job Analysis Agent.

Input : job title (optional) + free-text job description
Output: JobAnalysis (validated)

Rules + taxonomy first (always available). If an LLM is configured, the
service layer may ask it to *suggest* extra skills; those suggestions are only
kept if they exist in the taxonomy (see services/job_service.py).
"""
from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.ai.parsing.sections import BULLET, clean_text, strip_bullet
from app.ai.taxonomy import get_taxonomy

REQ_HEADINGS = ["requirements", "required skills", "must have", "must-have", "qualifications", "what you need",
                "basic qualifications", "minimum qualifications", "required qualifications", "skills required",
                "who you are", "what we're looking for", "what we are looking for", "skills", "technical skills",
                "key skills", "requirements and skills"]
PREF_HEADINGS = ["preferred", "preferred skills", "preferred qualifications", "nice to have", "nice-to-have",
                 "good to have", "bonus", "bonus points", "plus", "additional skills", "desired skills"]
RESP_HEADINGS = ["responsibilities", "key responsibilities", "what you will do", "what you'll do", "role",
                 "duties", "the role", "your role", "job responsibilities", "day to day"]
ABOUT_HEADINGS = ["about us", "about the company", "benefits", "perks", "what we offer", "why join us", "about"]
PREF_CUE = re.compile(r"\b(preferred|nice to have|good to have|bonus|a plus|is a plus|plus point|desirable|optional)\b", re.I)
EXP_RE = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*)?\+?\s*(?:years?|yrs?)", re.I)
EDU_LEVELS = [
    ("phd", r"\bph\.?\s?d\b|\bdoctorate\b"),
    ("masters", r"\bmaster'?s?\b|\bm\.?\s?tech\b|\bm\.?s\.?\b|\bmca\b|\bmba\b|\bpost\s?graduate\b"),
    ("bachelors", r"\bbachelor'?s?\b|\bb\.?\s?tech\b|\bb\.?\s?e\.?\b|\bb\.?sc\b|\bbca\b|\bgraduate\b|\bdegree\b|\bundergraduate\b"),
    ("diploma", r"\bdiploma\b"),
]
EDU_FIELDS = ["computer science", "information technology", "computer engineering", "software engineering",
              "electronics", "electrical", "data science", "artificial intelligence", "mathematics", "statistics",
              "engineering", "computer applications", "related field"]


class JobAnalysis(BaseModel):
    title: str | None = None
    department: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    minimum_experience: float | None = None
    education_requirements: list[dict] = Field(default_factory=list)  # [{"level":..., "fields":[...]}]
    responsibilities: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    unrecognized_terms: list[str] = Field(default_factory=list)
    method: str = "rules"


def _heading_kind(line: str) -> str | None:
    raw = strip_bullet(line).strip()
    if not raw or len(raw) > 60:
        return None
    norm = re.sub(r"[:\-–—|]+$", "", raw.lower()).strip()
    norm = re.sub(r"\s*\(.*\)$", "", norm)
    for kind, heads in (("preferred", PREF_HEADINGS), ("required", REQ_HEADINGS),
                        ("responsibilities", RESP_HEADINGS), ("about", ABOUT_HEADINGS)):
        if norm in heads:
            return kind
    return None


class JobAnalysisAgent:
    name = "job_analysis"
    version = "job-rules-1.0"

    def analyze(self, description: str, title: str | None = None) -> JobAnalysis:
        tax = get_taxonomy()
        text = clean_text(description or "")
        lines = text.split("\n")
        out = JobAnalysis(title=title.strip() if title else None)

        if not out.title and lines:
            first = strip_bullet(lines[0])
            if first and len(first.split()) <= 8 and not _heading_kind(first):
                out.title = first.strip(" :")
        dm = re.search(r"\bdepartment\s*[:\-]\s*([A-Za-z &/]{2,60})", text, re.I) or re.search(
            r"\bteam\s*[:\-]\s*([A-Za-z &/]{2,60})", text, re.I)
        if dm:
            out.department = dm.group(1).strip()

        section = "general"
        required: list[str] = []
        preferred: list[str] = []
        soft: list[str] = []
        for line in lines:
            kind = _heading_kind(line)
            if kind:
                section = kind
                continue
            clean = strip_bullet(line)
            if not clean or section == "about":
                continue
            is_list_line = bool(BULLET.match(line)) or "," in clean or section in ("required", "preferred")
            if section == "responsibilities" and BULLET.match(line):
                out.responsibilities.append(clean[:300])
            line_pref = section == "preferred" or bool(PREF_CUE.search(clean))
            if re.search(r"\bcertif", clean, re.I):
                out.certifications.append(clean[:200])
            for key, _m, _p in tax.find_in_text(clean, allow_ambiguous=is_list_line):
                skill = tax.skills[key]
                if skill.category == "soft_skill":
                    if key not in soft:
                        soft.append(key)
                    continue
                if line_pref:
                    if key not in preferred and key not in required:
                        preferred.append(key)
                else:
                    if key in preferred:
                        preferred.remove(key)
                    if key not in required:
                        required.append(key)

        out.required_skills = [tax.display(k) for k in required]
        out.preferred_skills = [tax.display(k) for k in preferred]
        out.soft_skills = [tax.display(k) for k in soft]

        exp_vals = []
        for m in EXP_RE.finditer(text):
            ctx = text[max(0, m.start() - 60): m.end() + 60].lower()
            if "experience" in ctx or "exp" in ctx:
                exp_vals.append(float(m.group(1)))
        if exp_vals:
            out.minimum_experience = min(exp_vals)
        elif re.search(r"\b(fresher|freshers|entry[- ]level|no experience required|0\s*years)\b", text, re.I):
            out.minimum_experience = 0.0

        low = text.lower()
        for level, pat in EDU_LEVELS:
            if re.search(pat, low):
                fields = [f for f in EDU_FIELDS if f in low]
                out.education_requirements.append({"level": level, "fields": fields})
                break
        return out
