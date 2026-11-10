# API documentation

Interactive docs (Swagger): **http://127.0.0.1:8000/docs** · OpenAPI JSON: `/openapi.json`.
All endpoints are under `/api/v1`. Authentication is an HTTP-only cookie set by login/register.
Errors always look like `{"error": {"code": "...", "message": "...", "details": [...]}}`.
Lists support `page` and `page_size` and return `{items, total, page, page_size}`.

Roles: **R** = recruiter, **C** = candidate, **A** = any logged-in user.

## Auth
| Method | Path | Who | Notes |
|---|---|---|---|
| POST | /auth/register | – | name, email, password (≥8), role. Rate limited |
| POST | /auth/login | – | Rate limited. Same error for wrong email or password |
| POST | /auth/logout | – | Clears cookie |
| GET | /auth/me | A | Current user |

## Jobs
| Method | Path | Who | Notes |
|---|---|---|---|
| POST | /jobs | R | `analyze: true` fills empty fields from the description |
| GET | /jobs | A | R: own jobs (filter `status`, `q`, `sort`); C: published only |
| GET/PUT/DELETE | /jobs/{id} | R (GET: A) | PUT marks the job as manually edited |
| POST | /jobs/{id}/publish · /unpublish · /close | R | Publish needs ≥1 required skill |
| POST | /jobs/{id}/analyze | R | `{description?, apply}` – preview or save extracted requirements |
| POST | /jobs/analyze-text | R | Analyze a pasted description before the job exists |

## Resumes
| Method | Path | Who | Notes |
|---|---|---|---|
| POST | /resumes/upload | A | multipart `file`; recruiters must send `job_id`. 201, or 400/409/413 with a code |
| POST | /jobs/{id}/resumes/bulk-upload | R | multipart `files` (≤50). **207** with one result per file |
| GET | /resumes/{id} | A | `include_text=true` adds extracted text |
| GET | /resumes/{id}/status | A | parsing status, error, skills found, warnings |
| GET | /resumes/{id}/file | A | original file (PDF inline, DOCX attachment) |
| POST | /resumes/{id}/reprocess | A | parse again (manual corrections are kept) |

Upload error codes: `unsupported_type`, `bad_signature`, `empty_file`, `file_too_large`, `corrupted_file`, `duplicate`, `job_required`.

## Candidates
| Method | Path | Who | Notes |
|---|---|---|---|
| GET | /candidates | R | filters `q, job_id, stage, skill, min_experience`; `sort` = `-created_at, name, -experience, experience, -score` (score needs `job_id`) |
| GET | /candidates/me | C | own profile |
| GET/PUT/DELETE | /candidates/{id} | A | PUT = manual correction (fields become `manually_verified`). DELETE removes files too; recruiters cannot delete account-owned profiles |
| GET/PUT | /candidates/{id}/skills | A | PUT replaces the list |
| GET | /candidates/{id}/skill-graph?job_id= | A | taxonomy-only graph + learning paths |

## Applications & pipeline
| Method | Path | Who |
|---|---|---|
| POST | /jobs/{id}/apply | C (needs a parsed resume) |
| GET | /jobs/{id}/applications | R |
| GET | /applications/me | C |
| PATCH | /applications/{id}/stage | R – `{stage, note?}`, logged in history |
| GET | /applications/{id}/history | R |
| DELETE | /applications/{id} | R – removes the candidate from this job |

## Matching
| Method | Path | Who |
|---|---|---|
| POST | /matching/jobs/{id}/run | R |
| GET | /matching/jobs/{id}/results | R – ranked |
| GET | /matching/{match_id} | A (candidate: own only) |
| POST | /matching/compare | R – `{job_id, candidate_ids: 2–4}` |

## Interviews
| Method | Path | Who |
|---|---|---|
| POST | /interviews | R (assigned) / C (practice) – `{application_id, interview_type, question_count 3–15, difficulty, categories}` |
| GET | /interviews | A – filter `status` |
| GET | /interviews/{id} | A – candidates see assigned questions only after starting |
| POST | /interviews/{id}/generate-questions | manager – `{use_llm?}`; returns `notice` when the question bank was used |
| PUT | /interviews/{id}/questions | manager, before start |
| POST | /interviews/{id}/start | candidate |
| GET | /interviews/{id}/current | candidate – current question, draft, seconds remaining |
| PUT | /interviews/{id}/answers/{qid}/draft | candidate – autosave |
| POST | /interviews/{id}/answers/{qid} | candidate – final answer; may add a follow-up |
| POST | /interviews/{id}/complete | candidate – starts background evaluation |
| POST | /interviews/{id}/evaluate | manager – evaluate pending answers |

## Reports
| Method | Path | Who |
|---|---|---|
| GET | /reports | R – `q`, `job_id` |
| POST | /reports/generate | R – `{application_id, interview_id?}` |
| GET | /reports/{id} | R |
| POST | /reports/{id}/notes | R – recruiter comment |
| GET | /reports/{id}/pdf | R – PDF download |

## Analytics, settings, learning, audit
| Method | Path | Who |
|---|---|---|
| GET | /analytics/overview · /jobs · /pipeline · /skills · /interviews | R |
| GET | /settings | R |
| PUT | /settings/weights · /settings/rubric | R – `{weights: {...}}`, must sum to 100 |
| GET | /settings/llm-status | A – provider, model, availability (never keys) |
| GET | /learning/recommendations?application_id= | A |
| POST | /learning/progress | C – `{resource_key, completed}` |
| GET | /ai-audit | R |
| GET | /api/health | – | (outside /v1) DB check |
