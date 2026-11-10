# Testing

## Backend (Pytest) – 107 tests
Runs against a real PostgreSQL test database (`TEST_DATABASE_URL`). The suite migrates it from scratch,
empties all tables after each test, and refuses to run if it equals `DATABASE_URL`. LLM calls use a
**fake provider (test double)**; the real embedding model and spaCy are used.

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m pytest
# Python vector fallback (needs a second empty test database):
$env:VECTOR_BACKEND="python"; $env:TEST_DATABASE_URL="postgresql+psycopg://postgres:PW@localhost:5432/agenthire_test_py"; python -m pytest
```

| File | Covers |
|---|---|
| `unit/test_security.py` | Argon2, JWT expiry/tampering, input rules |
| `unit/test_parsing.py` | cleaning, sections, taxonomy (synonyms, related, ambiguous names, C++/C#), field extraction, overlapping/intern experience, PDF/DOCX extraction, corrupted/empty files, file signatures, chunk size, job analysis |
| `unit/test_matching.py` | each score component, Django-vs-FastAPI "related not equal", traceable totals, weight validation, keyword baseline, personal data does not change the score |
| `ai/test_llm_and_bank.py` | JSON extraction, untrusted-text wrapping, schema retry then success / give up, no-provider, rubric weights, concept coverage, question bank size, bank selection and project grounding |
| `api/test_auth.py` | register/login/logout, errors, disabled user, rate limit, profile linking, audit log |
| `api/test_jobs.py` | CRUD, analysis, publish rules, validation, recruiter isolation, candidate visibility, search/pagination |
| `api/test_resumes_candidates.py` | upload → parse → profile, DOCX, bad/oversize/fake files, scanned PDF, duplicates, bulk 207, merge by email, manual corrections survive reprocess, privacy, download, filters, delete removes files |
| `api/test_pipeline.py` | stage history, invalid stage, permissions, no auto-reject |
| `api/test_matching_api.py` | ranking, explanation, RAG evidence, rerun, custom weights, compare, permissions, candidate own match |
| `api/test_interviews.py` | question bank, full flow with fake LLM (follow-up, drafts/resume, duplicate submit, weighted score computed by code, fake quotes dropped, audit), prompt-injection wrapping, no-LLM pending, invalid LLM output fallback, editing, practice, isolation |
| `api/test_reports_analytics.py` | report + notes + PDF text, permissions, analytics equal DB values, learning + progress, skill graph edges only from taxonomy, AI audit |

## Frontend (Playwright) – 12 tests (+2 skipped by design)
1. Start the backend with rate limiting off (the tests create many accounts quickly):
   ```powershell
   cd backend; $env:RATE_LIMIT_ENABLED="false"; uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. Build and test:
   ```powershell
   cd frontend
   npx playwright install chromium   # first time
   npm run build
   npm run test:e2e
   ```
- `auth.spec.ts` (desktop + mobile Pixel 7): landing, validation, recruiter/candidate registration, role redirects, logout/login, duplicate email.
- `flows.spec.ts` (desktop): **full recruiter flow** – register → create job with extraction → publish → bulk upload → parsing → run matching → explanation → profile correction → create interview → candidate takes it → pending evaluation (no LLM) → report + comment → PDF download → stage change with confirmation → dashboard count; **full candidate flow** – register → upload resume → apply → practice interview → autosave survives reload → finish → feedback → no access to recruiter pages.
  The two flow tests are skipped in the mobile project on purpose (one run is enough; mobile layout is covered by `auth.spec.ts` and manual screenshots).

## Other checks
- `npx tsc --noEmit` and `npm run lint` – clean.
- `npm run build` – succeeds.
- `python ../scripts/evaluate_matching.py --compare-models` – see `matching_evaluation.md`.
- `python ../scripts/check_learning_links.py` – checks curated URLs (needs internet).
- Fresh install check: new database → `alembic upgrade head` → `seed_demo_data.py` (20 s) → second run is a no-op → `--reset` recreates.

## Last run (2026-11-02, Linux build machine)
| Suite | Result |
|---|---|
| Backend pytest, pgvector | **107 passed**, 0 failed |
| Backend pytest, Python vector fallback | **107 passed**, 0 failed |
| Playwright | **12 passed**, 0 failed, 2 skipped (by design) |
| TypeScript / ESLint / build | clean / clean / success |
| Fresh DB + migrate + seed + reseed + reset | success |

**Not tested here:** a real Ollama or Gemini model (not available on the build machine). The LLM code paths
are covered with the fake provider. Please run one interview with Ollama on your machine and check the
AI audit page shows `validation passed`.
