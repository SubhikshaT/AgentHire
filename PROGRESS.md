# AgentHire – Build Progress

Last updated: 2026-11-02 · Status: **all 7 phases done**

## Build machine
Python 3.13 (code is 3.11-compatible), Node 22 LTS, PostgreSQL 16 + pgvector 0.6.0, 7 GB RAM, no GPU,
**no Ollama** → LLM features tested with a fake provider and with `LLM_PROVIDER=none`.

## Phases
| # | Phase | Status | Verified by |
|---|---|---|---|
| 1 | Foundation: structure, config, 19-table schema, Alembic, auth, frontend shell | ✅ | migrate up/down both vector modes; auth unit + API tests; E2E auth |
| 2 | Jobs + resume upload/parsing + candidate profiles | ✅ | parsing unit tests; upload/bulk/duplicate/scanned/merge API tests; manual check in UI |
| 3 | Matching (hybrid score, explanation, RAG evidence), explorer, compare, pipeline | ✅ | matching unit + API tests; evaluation script |
| 4 | Interviews: generation (LLM/bank), runner, autosave, follow-ups, evaluation | ✅ | fake-LLM full flow, invalid-output fallback, injection test, no-LLM pending |
| 5 | Reports, PDF, notes, dashboard, settings | ✅ | API tests incl. PDF text; E2E PDF download |
| 6 | Nice to Have: analytics, skill graph, learning, practice, AI audit page | ✅ | API tests; analytics numbers checked against DB |
| 7 | Data, seed, evaluation, docs, full test run, packaging | ✅ | fresh DB → migrate → seed → reseed no-op → reset; all suites green |

## Final test results (2026-11-02)
| Suite | Result |
|---|---|
| Backend pytest (pgvector) | 107 passed |
| Backend pytest (`VECTOR_BACKEND=python`) | 107 passed |
| Playwright (desktop + mobile) | 12 passed, 2 skipped by design (long flows run on desktop only) |
| `tsc --noEmit`, ESLint, `next build` | clean |

## Matching evaluation (synthetic, K=5)
Hybrid P@5 0.900 / NDCG@5 0.930 vs keyword 0.720 / 0.757. `all-mpnet-base-v2` gives about the same hybrid
result but is ~6× slower, so MiniLM stays the default.

## Key decisions
- Scores always computed by code; the LLM only writes questions/feedback and gives validated rubric marks.
- Skill "related" links give half credit and are shown as "related, not equivalent".
- Without an LLM, answers stay pending instead of getting a fake score.
- Name/email/phone never go into embeddings or prompts.
- Other users' records return 404, not 403.
- pgvector optional: `VECTOR_BACKEND=python` fallback, both tested.
- Next.js rewrites `/api/*` to FastAPI so the auth cookie is same-origin.
- Methodology version string shortened to fit `VARCHAR(40)`.

## Known gaps / to check on your laptop
1. Run one interview with Ollama (`qwen2.5:7b`) and check the AI audit page shows "validation passed".
2. Windows install not run here (Linux build). Commands are written for PowerShell; see `docs/setup_windows.md`.
3. No OCR; rule-based parsing can miss fields on unusual layouts.
4. Add screenshots to the README.
