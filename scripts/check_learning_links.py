"""Check that every URL in backend/app/ai/data/learning_resources.json still responds.

Usage (backend venv active): python ../scripts/check_learning_links.py
Needs internet access. Prints one line per URL and exits 1 if any link is broken.
"""
import json
import sys
from pathlib import Path

import httpx

DATA = Path(__file__).resolve().parents[1] / "backend/app/ai/data/learning_resources.json"


def main() -> int:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    urls = sorted({r["url"] for k, v in data.items() if not k.startswith("_") for r in v})
    bad = 0
    with httpx.Client(follow_redirects=True, timeout=15, headers={"User-Agent": "AgentHire-link-check"}) as c:
        for u in urls:
            try:
                code = c.get(u).status_code
            except httpx.HTTPError as e:
                code = f"error: {e.__class__.__name__}"
            ok = isinstance(code, int) and code < 400
            blocked = code in (401, 403, 429)  # site refuses automated clients; open it in a browser
            bad += not ok and not blocked
            print(f"{'OK ' if ok else 'CHK' if blocked else 'BAD'} {code} {u}")
    print(f"\n{bad} broken link(s) of {len(urls)}. 'CHK' = the site blocks scripts; check it in a browser.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
