"""Skill taxonomy: normalization, synonym lookup and 'related' links.

Loaded once from app/ai/data/skill_taxonomy.json.
- synonyms  -> the SAME skill (full credit in matching)
- related   -> a DIFFERENT, adjacent skill (partial credit, shown as "related, not equivalent")
Related links are made two-way when loading.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).parent / "data" / "skill_taxonomy.json"

# Aliases that are ordinary words or single letters. They only count when found
# inside a resume's skills section / a job's skills list, never in free prose.
AMBIGUOUS_ALIASES = {
    "c", "r", "go", "rest", "node", "spring", "oracle", "cloud", "backend", "frontend", "front end",
    "back end", "ml", "dl", "tf", "torch", "ts", "js", "py", "os concepts", "embedded", "android", "ios",
    "communication", "presentation", "flexibility", "collaboration", "analytics", "visualization",
    "normalization", "probability", "networking", "firewalls", "authentication", "authorization",
    "containers", "prioritization", "mentoring", "express", "rails", "swift", "dart", "flask", "excel",
    "kafka", "airflow", "spark", "elk", "solid", "eda", "iac", "cloud", "full stack", "kanban",
}


def normalize_text(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[‐-―]", "-", s)
    s = re.sub(r"\s+", " ", s)
    return s


@dataclass
class SkillDef:
    key: str
    display: str
    category: str
    synonyms: list[str]
    related: set[str] = field(default_factory=set)


class Taxonomy:
    def __init__(self, raw: dict):
        self.version: str = raw.get("_meta", {}).get("version", "unknown")
        self.skills: dict[str, SkillDef] = {}
        for key, v in raw.items():
            if key.startswith("_"):
                continue
            self.skills[key] = SkillDef(
                key=key,
                display=v["display"],
                category=v["category"],
                synonyms=list(v.get("synonyms", [])),
                related=set(v.get("related", [])),
            )
        # make related two-way, drop unknown keys and self-links
        for key, s in list(self.skills.items()):
            for r in list(s.related):
                if r not in self.skills or r == key:
                    s.related.discard(r)
                else:
                    self.skills[r].related.add(key)
        # alias -> key
        self.alias_to_key: dict[str, str] = {}
        for key, s in self.skills.items():
            for alias in {key.replace("_", " "), s.display, *s.synonyms}:
                a = normalize_text(alias)
                if a and a not in self.alias_to_key:
                    self.alias_to_key[a] = key
        self._patterns = self._build_patterns()

    # ---------- lookup ----------
    def resolve(self, name: str) -> str | None:
        """Map a free-text skill name to its taxonomy key, or None if unknown."""
        n = normalize_text(name)
        if n in self.alias_to_key:
            return self.alias_to_key[n]
        n2 = re.sub(r"[^a-z0-9+#./ -]", "", n).strip(" .-")
        return self.alias_to_key.get(n2)

    def display(self, key: str) -> str:
        s = self.skills.get(key)
        return s.display if s else key

    def are_related(self, a: str, b: str) -> bool:
        return a in self.skills and b in self.skills[a].related

    def normalize_list(self, names: list[str]) -> tuple[list[str], list[str]]:
        """Return (known keys, unknown raw names), de-duplicated, order kept."""
        known: list[str] = []
        unknown: list[str] = []
        for n in names:
            k = self.resolve(n)
            if k:
                if k not in known:
                    known.append(k)
            elif n.strip() and n.strip() not in unknown:
                unknown.append(n.strip())
        return known, unknown

    # ---------- text scanning ----------
    def _build_patterns(self):
        pats = []
        for alias, key in self.alias_to_key.items():
            esc = re.escape(alias).replace(r"\ ", r"[\s\-]+")
            # word boundaries that also respect symbols like C++, C#, .NET
            pat = re.compile(rf"(?<![A-Za-z0-9+#.]){esc}(?![A-Za-z0-9+#])", re.IGNORECASE)
            pats.append((alias, key, pat))
        # longer aliases first so "react native" wins over "react"
        pats.sort(key=lambda t: -len(t[0]))
        return pats

    def find_in_text(self, text: str, allow_ambiguous: bool) -> list[tuple[str, str, int]]:
        """Find skills mentioned in text. Returns (key, matched text, position).

        Single letters (C, R) must be written in upper case to count.
        """
        found: dict[str, tuple[str, str, int]] = {}
        taken: list[tuple[int, int]] = []
        for alias, key, pat in self._patterns:
            if alias in AMBIGUOUS_ALIASES and not allow_ambiguous:
                continue
            for m in pat.finditer(text):
                s, e = m.span()
                if any(s < te and e > ts for ts, te in taken):
                    continue
                if len(alias) == 1 and m.group(0) != alias.upper():
                    continue
                taken.append((s, e))
                if key not in found:
                    found[key] = (key, m.group(0), s)
        return sorted(found.values(), key=lambda t: t[2])


@lru_cache
def get_taxonomy() -> Taxonomy:
    return Taxonomy(json.loads(DATA.read_text(encoding="utf-8")))
