"""Resume Intelligence Agent.

Input : cleaned resume text
Output: ParsedResume (validated Pydantic model)

Deterministic: rules + spaCy NER + the skill taxonomy. Nothing is invented:
fields that are not found stay null / empty. Resume text is treated as data only
(this agent never sends it to an LLM).
"""
from __future__ import annotations

import re
from datetime import date

from app.ai.nlp import get_spacy
from app.ai.parsing.sections import clean_text, split_sections, strip_bullet
from app.ai.schemas.resume import (
    CertificationEntry,
    EducationEntry,
    ExperienceEntry,
    ExtractedSkill,
    ParsedResume,
    ProjectEntry,
)
from app.ai.taxonomy import get_taxonomy

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<![\w])(\+?\d[\d\s().\-]{8,17}\d)(?![\w])")
YEAR_RE = re.compile(r"\b(19[6-9]\d|20[0-4]\d)\b")
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
MONTH_PAT = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
DATE_PAT = rf"(?:{MONTH_PAT}\.?\s*,?\s*(\d{{4}})|(\d{{1,2}})[/\-.](\d{{4}})|(\d{{4}}))"
RANGE_RE = re.compile(
    rf"{DATE_PAT}\s*(?:-|–|—|to|till|until)\s*(?:{DATE_PAT}|(present|current|now|ongoing|till date|date))",
    re.IGNORECASE,
)

DEGREE_LEVELS = [
    ("phd", r"\b(ph\.?\s?d|doctor(?:ate)? of)\b"),
    ("masters", r"\b(m\.?\s?tech|m\.?\s?e\b|m\.?\s?sc|m\.?\s?s\b|mca|mba|master'?s?|m\.?\s?com|post\s?graduate|pg diploma)"),
    ("bachelors", r"\b(b\.?\s?tech|b\.?\s?e\b|b\.?\s?sc|b\.?\s?s\b|bca|bba|bachelor'?s?|b\.?\s?com|undergraduate|b\.?\s?a\b)"),
    ("diploma", r"\bdiploma\b"),
    ("higher_secondary", r"\b(hsc|higher secondary|12th|class xii|xii|intermediate|senior secondary|a[- ]levels?)\b"),
    ("secondary", r"\b(sslc|ssc|10th|class x\b|matriculation|secondary school|cbse|icse|gcse)\b"),
]
FIELD_RE = re.compile(
    r"\b(?:in|of)\s+([A-Z][A-Za-z&/ ]{2,60}?)(?=\s*(?:[,|(\-–]|\d|$|from|at\b))"
)
COMMON_FIELDS = [
    "computer science and engineering", "computer science", "information technology", "artificial intelligence and data science",
    "artificial intelligence", "data science", "electronics and communication", "electronics", "electrical",
    "mechanical", "civil", "software engineering", "computer applications", "mathematics", "statistics", "physics",
    "business administration", "commerce", "information systems",
]
INSTITUTION_WORDS = re.compile(r"\b(university|college|institute|school|academy|iit|nit|iiit|polytechnic|vidyalaya)\b", re.I)
ROLE_WORDS = re.compile(
    r"\b(engineer|developer|analyst|intern|scientist|manager|lead|architect|designer|tester|consultant|"
    r"programmer|administrator|specialist|associate|trainee|officer|executive)\b", re.I)
INTERN_RE = re.compile(r"\bintern(ship)?\b", re.I)
CERT_ISSUERS = ["coursera", "udemy", "nptel", "aws", "google", "microsoft", "oracle", "cisco", "ibm", "edx",
                "linkedin learning", "hackerrank", "meta", "infosys", "freecodecamp", "great learning", "simplilearn"]


def _ym(month_txt: str | None, year_txt: str | None, num_month: str | None = None) -> tuple[int, int] | None:
    if not year_txt:
        return None
    y = int(year_txt)
    m = 1
    if month_txt:
        m = MONTHS.get(month_txt[:3].lower(), 1)
    elif num_month:
        m = max(1, min(12, int(num_month)))
    return y, m


def _parse_range(text: str, today: date) -> tuple[tuple[int, int], tuple[int, int], bool, str] | None:
    m = RANGE_RE.search(text)
    if not m:
        return None
    g = m.groups()
    start = _ym(g[0], g[1]) or _ym(None, g[3], g[2]) or _ym(None, g[4])
    present = bool(g[10])
    if present:
        end = (today.year, today.month)
    else:
        end = _ym(g[5], g[6]) or _ym(None, g[8], g[7]) or _ym(None, g[9])
        if end and not (g[5] or g[7]) and g[9]:
            end = (end[0], 12) if end[0] != start[0] else (end[0], 12)
    if not start or not end or end < start:
        return None
    return start, end, present, m.group(0)


def _months_between(a: tuple[int, int], b: tuple[int, int]) -> int:
    return (b[0] - a[0]) * 12 + (b[1] - a[1]) + 1


def _merge_total_months(intervals: list[tuple[tuple[int, int], tuple[int, int]]]) -> int:
    """Total months with overlapping periods counted once."""
    if not intervals:
        return 0
    ivs = sorted(intervals)
    total = 0
    cur_s, cur_e = ivs[0]
    for s, e in ivs[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            total += _months_between(cur_s, cur_e)
            cur_s, cur_e = s, e
    total += _months_between(cur_s, cur_e)
    return total


class ResumeIntelligenceAgent:
    name = "resume_intelligence"
    version = "resume-rules-1.0"

    def __init__(self, today: date | None = None):
        self.today = today or date.today()
        self.tax = get_taxonomy()

    # ---------------- public ----------------
    def parse(self, raw_text: str) -> ParsedResume:
        text = clean_text(raw_text)
        sections = split_sections(text)
        out = ParsedResume(sections_found=[s for s in sections if s != "header"])
        header = sections.get("header", "")
        out.email = self._email(text)
        out.phone = self._phone(header or text[:600])
        out.candidate_name = self._name(header or text[:400], out.email)
        out.professional_summary = self._summary(sections.get("summary"))
        out.skills = self._skills(sections)
        out.education = self._education(sections.get("education", ""))
        out.work_experience = self._experience(sections.get("experience", ""))
        out.projects = self._projects(sections.get("projects", ""))
        out.certifications = self._certifications(sections.get("certifications", ""))
        out.total_experience_years = self._total_years(out.work_experience)
        if "skills" not in sections:
            out.warnings.append("No skills section found; skills were taken from the rest of the resume only.")
        if not out.email:
            out.warnings.append("No email address found.")
        return out

    # ---------------- contact ----------------
    def _email(self, text: str) -> str | None:
        m = EMAIL_RE.search(text)
        return m.group(0).lower().rstrip(".") if m else None

    def _phone(self, text: str) -> str | None:
        for m in PHONE_RE.finditer(text):
            cand = m.group(1)
            digits = re.sub(r"\D", "", cand)
            if 10 <= len(digits) <= 15 and not YEAR_RE.fullmatch(cand.strip()):
                # avoid date ranges like 2019 - 2023
                if re.fullmatch(r"\s*(19|20)\d{2}\s*[-–]\s*(19|20)\d{2}\s*", cand):
                    continue
                return re.sub(r"\s+", " ", cand.strip())
        return None

    def _name(self, header: str, email: str | None) -> str | None:
        lines = [ln.strip() for ln in header.split("\n") if ln.strip()][:6]

        def looks_like_name(s: str) -> bool:
            s = s.strip()
            if not s or any(ch.isdigit() for ch in s) or "@" in s or len(s) > 50:
                return False
            if self.tax.resolve(s):
                return False
            words = s.replace(".", ". ").split()
            if not (1 < len(words) <= 5):
                return False
            if any(w.lower() in {"resume", "curriculum", "vitae", "cv", "profile", "engineer", "developer"} for w in words):
                return False
            return all(w[0].isupper() for w in words if w[0].isalpha())

        nlp = get_spacy()
        if nlp is not None:
            for ln in lines[:3]:
                doc = nlp(ln)
                for ent in doc.ents:
                    if ent.label_ == "PERSON" and looks_like_name(ent.text):
                        return ent.text.strip().title() if ent.text.isupper() else ent.text.strip()
        for ln in lines[:3]:
            part = re.split(r"\s[|•·,]\s|\s{3,}", ln)[0]
            if looks_like_name(part):
                return part.title() if part.isupper() else part
        return None

    def _summary(self, s: str | None) -> str | None:
        if not s:
            return None
        return re.sub(r"\s+", " ", s).strip()[:1500] or None

    # ---------------- skills ----------------
    def _skills(self, sections: dict[str, str]) -> list[ExtractedSkill]:
        found: dict[str, ExtractedSkill] = {}
        order = ["skills", "experience", "projects", "certifications", "summary", "education", "achievements", "header", "other"]
        for sec in order + [s for s in sections if s not in order]:
            body = sections.get(sec)
            if not body or sec == "other":
                continue
            allow = sec == "skills"
            for line in body.split("\n"):
                line_clean = strip_bullet(line)
                if not line_clean:
                    continue
                for key, matched, _pos in self.tax.find_in_text(line_clean, allow_ambiguous=allow):
                    if key in found:
                        continue
                    found[key] = ExtractedSkill(
                        key=key,
                        name=self.tax.display(key),
                        matched_text=matched,
                        evidence_text=line_clean[:300],
                        evidence_section=sec,
                    )
        return list(found.values())

    # ---------------- education ----------------
    def _education(self, body: str) -> list[EducationEntry]:
        if not body:
            return []
        lines = [strip_bullet(ln) for ln in body.split("\n") if strip_bullet(ln)]
        entries: list[list[str]] = []
        for ln in lines:
            starts_new = any(re.search(p, ln, re.I) for _, p in DEGREE_LEVELS) or (
                INSTITUTION_WORDS.search(ln) and entries and any(
                    re.search(p, " ".join(entries[-1]), re.I) for _, p in DEGREE_LEVELS)
                and INSTITUTION_WORDS.search(" ".join(entries[-1]))
            )
            if starts_new or not entries:
                entries.append([ln])
            else:
                entries[-1].append(ln)
        result = []
        for group in entries:
            raw = " | ".join(group)
            level = next((lvl for lvl, p in DEGREE_LEVELS if re.search(p, raw, re.I)), None)
            if level is None and not INSTITUTION_WORDS.search(raw):
                continue
            degree_line = next((g for g in group if any(re.search(p, g, re.I) for _, p in DEGREE_LEVELS)), None)
            inst = next((g for g in group if INSTITUTION_WORDS.search(g)), None)
            if inst:
                splitter = r"\s[|–\-]\s|,\s" if inst == degree_line else r"\s*\|\s*|\s[–\-]\s"
                parts = [p for p in re.split(splitter, inst) if p.strip()]
                inst = next((p for p in parts if INSTITUTION_WORDS.search(p)), None)
                if inst:
                    inst = re.sub(r"\b(cgpa|gpa|percentage)\b.*$", "", inst, flags=re.I)
                    inst = re.sub(r"[\d.]+\s*%", "", inst)
            years = [int(y) for y in YEAR_RE.findall(raw)]
            fld = None
            low = raw.lower()
            for f in COMMON_FIELDS:
                if f in low:
                    fld = f.title().replace(" And ", " and ")
                    break
            if not fld and degree_line:
                m = FIELD_RE.search(degree_line)
                if m:
                    fld = m.group(1).strip()
            score = None
            sm = re.search(r"\b(cgpa|gpa|percentage|score)\s*[:\-]?\s*([\d.]+\s*(?:/\s*\d+|%)?)", raw, re.I) or re.search(
                r"\b([\d.]{2,5}\s*%)", raw)
            if sm:
                score = sm.group(0).strip()
            degree = None
            if degree_line:
                degree = re.split(r"\s[|–\-]\s|,\s*(?=[A-Z][a-z]+ (?:University|College|Institute))", degree_line)[0].strip()
                degree = re.sub(YEAR_RE, "", degree).strip(" -–,|")
                degree = re.sub(r"\(\s*\)", "", degree).strip()
            result.append(EducationEntry(
                degree=degree or None, level=level, field=fld,
                institution=(re.sub(YEAR_RE, "", inst).strip(" -–,|()") if inst else None),
                start_year=min(years) if len(years) > 1 else None,
                end_year=max(years) if years else None,
                score=score, raw_text=raw[:400],
            ))
        return result

    # ---------------- experience ----------------
    def _experience(self, body: str) -> list[ExperienceEntry]:
        if not body:
            return []
        lines = [ln for ln in body.split("\n")]
        blocks: list[dict] = []
        pending_header: list[str] = []
        for ln in lines:
            clean = strip_bullet(ln)
            if not clean:
                continue
            is_bullet = clean != ln.strip()
            rng = _parse_range(clean, self.today)
            if rng:
                header_txt = clean.replace(rng[3], " ").strip(" |,–-()")
                head_lines = pending_header + ([header_txt] if header_txt else [])
                blocks.append({"range": rng, "head": head_lines, "desc": []})
                pending_header = []
            elif blocks and (is_bullet or len(clean.split()) > 8):
                blocks[-1]["desc"].append(clean)
            elif not is_bullet and len(clean.split()) <= 10:
                # short non-bullet line: header of the next entry (title / company)
                if blocks and not blocks[-1]["desc"] and len(blocks[-1]["head"]) < 2:
                    blocks[-1]["head"].append(clean)
                else:
                    pending_header.append(clean)
                    pending_header = pending_header[-2:]
            elif blocks:
                blocks[-1]["desc"].append(clean)
        result = []
        for b in blocks:
            start, end, present, _ = b["range"]
            head = [h for h in b["head"] if h]
            title, company = self._title_company(head)
            raw = " | ".join(head + b["desc"])
            result.append(ExperienceEntry(
                title=title, company=company,
                start=f"{start[0]:04d}-{start[1]:02d}",
                end="present" if present else f"{end[0]:04d}-{end[1]:02d}",
                months=_months_between(start, end),
                description=" ".join(b["desc"])[:1500],
                is_internship=bool(INTERN_RE.search(raw)),
                raw_text=raw[:600],
            ))
        return result

    def _title_company(self, head: list[str]) -> tuple[str | None, str | None]:
        if not head:
            return None, None
        joined = " | ".join(head)
        m = re.match(r"(.+?)\s+(?:at|@)\s+(.+)", joined, re.I)
        if m:
            return m.group(1).strip(" |,-–"), m.group(2).strip(" |,-–")
        parts = [p.strip() for p in re.split(r"\s*[|,–—]\s*|\s+-\s+", joined) if p.strip()]
        if len(parts) >= 2:
            a, b = parts[0], parts[1]
            if ROLE_WORDS.search(b) and not ROLE_WORDS.search(a):
                a, b = b, a  # "Company, Title" order
            return a, b
        return parts[0] if parts else None, None

    def _total_years(self, exp: list[ExperienceEntry]) -> float | None:
        """Full-time experience only (internships are excluded). None if no dated entries."""
        if not exp:
            return None
        ivs = []
        for e in exp:
            if e.is_internship or not e.start:
                continue
            s = tuple(int(x) for x in e.start.split("-"))
            en = (self.today.year, self.today.month) if e.end == "present" else tuple(int(x) for x in e.end.split("-"))
            ivs.append((s, en))
        if not ivs:
            return 0.0
        return round(_merge_total_months(ivs) / 12, 1)

    # ---------------- projects ----------------
    def _projects(self, body: str) -> list[ProjectEntry]:
        if not body:
            return []
        projects: list[dict] = []
        for ln in body.split("\n"):
            clean = strip_bullet(ln)
            if not clean:
                continue
            is_bullet = clean != ln.strip()
            m = re.match(r"^([^:|–]{3,70}?)\s*[:|–]\s+(.{10,})$", clean)
            title_like = (not is_bullet and len(clean.split()) <= 9 and not clean.endswith("."))
            if m and not is_bullet:
                projects.append({"name": m.group(1).strip(), "desc": [m.group(2).strip()]})
            elif title_like:
                projects.append({"name": clean.strip(" |-–"), "desc": []})
            elif projects:
                projects[-1]["desc"].append(clean)
            else:
                projects.append({"name": clean[:70], "desc": [clean]})
        out = []
        for p in projects:
            desc = " ".join(p["desc"])
            text = p["name"] + " " + desc
            skills = [self.tax.display(k) for k, _, _ in self.tax.find_in_text(text, allow_ambiguous=False)]
            tech = re.search(r"(?:tech(?:nologies)?|stack|tools|built with)\s*(?:used)?\s*[:\-]\s*(.+)", text, re.I)
            if tech:
                skills += [self.tax.display(k) for k, _, _ in self.tax.find_in_text(tech.group(1), allow_ambiguous=True)]
            name = re.sub(r"\s*\(.*?\)\s*$", "", p["name"]).strip() or p["name"]
            out.append(ProjectEntry(name=name[:120], description=desc[:1500], skills=list(dict.fromkeys(skills))))
        return out

    # ---------------- certifications ----------------
    def _certifications(self, body: str) -> list[CertificationEntry]:
        out = []
        for ln in body.split("\n"):
            clean = strip_bullet(ln)
            if len(clean) < 4:
                continue
            years = YEAR_RE.findall(clean)
            issuer = next((i.title() if i not in {"aws", "ibm", "nptel"} else i.upper()
                           for i in CERT_ISSUERS if re.search(rf"\b{re.escape(i)}\b", clean, re.I)), None)
            name = re.sub(YEAR_RE, "", clean)
            name = re.sub(r"\(\s*\)", "", name)
            if name.count("(") != name.count(")"):
                name = name.replace("(", " ").replace(")", " ")
            name = re.sub(r"\s+", " ", name).strip(" -–|,")
            out.append(CertificationEntry(name=name[:200], issuer=issuer, year=int(years[-1]) if years else None))
        return out
