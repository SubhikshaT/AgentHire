"""Career / Learning Recommendation Agent.

Input : skill gaps (missing required/preferred skills, related-only skills)
Output: list of resources taken ONLY from data/learning_resources.json (never generated URLs)

Rule-based: required gaps first, then related-only, then preferred. If a gap has no direct
resource, resources of a closely related skill are used and labelled as such.
"""
import json
from functools import lru_cache
from pathlib import Path

from app.ai.taxonomy import get_taxonomy

DATA = Path(__file__).resolve().parents[1] / "data" / "learning_resources.json"
VERSION = "learn-rules-1.0"


@lru_cache
def load_resources() -> dict:
    return {k: v for k, v in json.loads(DATA.read_text(encoding="utf-8")).items() if not k.startswith("_")}


def all_resource_keys() -> set[str]:
    return {r["key"] for items in load_resources().values() for r in items}


def recommend(gaps: list[tuple[str, str]], limit: int = 12) -> list[dict]:
    """gaps: list of (skill name, priority) with priority in {'required', 'related', 'preferred'}."""
    tax = get_taxonomy()
    res = load_resources()
    order = {"required": 0, "related": 1, "preferred": 2}
    out, seen = [], set()
    for name, prio in sorted(gaps, key=lambda g: order.get(g[1], 3)):
        key = tax.resolve(name) or name.lower()
        items = res.get(key, [])
        via = None
        if not items and key in tax.skills:
            for rk in sorted(tax.skills[key].related):
                if res.get(rk):
                    items, via = res[rk], tax.display(rk)
                    break
        for r in items:
            if r["key"] in seen:
                continue
            seen.add(r["key"])
            out.append({**r, "skill": name, "priority": prio,
                        "note": f"No direct resource for {name}; this covers the related skill {via}." if via else None})
            if len(out) >= limit:
                return out
    return out
