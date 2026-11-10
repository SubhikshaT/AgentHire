"""Text cleaning and resume section detection (rule-based)."""
import re
import unicodedata

SECTION_HEADINGS: dict[str, list[str]] = {
    "summary": ["summary", "professional summary", "profile", "about me", "objective", "career objective",
                "professional profile", "career summary", "overview"],
    "skills": ["skills", "technical skills", "key skills", "core skills", "skill set", "skillset", "technologies",
               "tech stack", "technical proficiency", "competencies", "core competencies", "tools and technologies",
               "tools & technologies", "programming languages"],
    "experience": ["experience", "work experience", "professional experience", "employment history",
                   "work history", "employment", "internships", "internship", "internship experience",
                   "professional background", "career history"],
    "education": ["education", "academic background", "academic qualifications", "qualifications",
                  "educational qualifications", "academics", "education and training"],
    "projects": ["projects", "academic projects", "personal projects", "key projects", "project experience",
                 "selected projects", "project work"],
    "certifications": ["certifications", "certificates", "licenses and certifications", "courses",
                       "certifications and courses", "training", "licenses & certifications", "online courses"],
    "achievements": ["achievements", "awards", "honors", "accomplishments", "awards and achievements",
                     "extracurricular activities", "activities", "leadership", "publications"],
    "other": ["languages", "interests", "hobbies", "references", "declaration", "personal details",
              "personal information", "additional information", "volunteering", "volunteer experience"],
}

_HEADING_LOOKUP = {h: sec for sec, hs in SECTION_HEADINGS.items() for h in hs}
BULLET = re.compile(r"^\s*[•●▪◦‣⁃∙\-\*·>•◦▪➢✓]+\s*")


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    text = re.sub(r"[​‌‍﻿]", "", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # broken hyphenation
    lines = [re.sub(r"[  ]+", " ", ln).strip() for ln in text.split("\n")]
    out: list[str] = []
    for ln in lines:
        if not ln and out and not out[-1]:
            continue
        out.append(ln)
    return "\n".join(out).strip()


def heading_section(line: str) -> str | None:
    """Return the section name if this line is a section heading."""
    raw = BULLET.sub("", line).strip()
    if not raw or len(raw) > 45:
        return None
    norm = re.sub(r"[:\-–—|_=#*]+$", "", raw.lower()).strip()
    norm = re.sub(r"^[^a-z]+", "", norm)
    norm = re.sub(r"\s+", " ", norm)
    if norm in _HEADING_LOOKUP:
        return _HEADING_LOOKUP[norm]
    return None


def split_sections(text: str) -> dict[str, str]:
    """Split cleaned resume text into sections. Text before the first heading is 'header'."""
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in text.split("\n"):
        sec = heading_section(line)
        if sec:
            current = sec
            sections.setdefault(current, [])
            continue
        # "Skills: Python, Java" - heading and content on the same line
        raw = BULLET.sub("", line).strip()
        if ":" in raw and not BULLET.match(line):
            head, rest = raw.split(":", 1)
            inline = heading_section(head)
            if inline == "skills" and rest.strip() and current != "skills":
                current = inline
                sections.setdefault(current, []).append(rest.strip())
                continue
        sections.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


def strip_bullet(line: str) -> str:
    return BULLET.sub("", line).strip()
