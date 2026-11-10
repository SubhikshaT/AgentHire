# Synthetic sample data

**Everything in this folder is synthetic.** All people, emails, phone numbers, companies and
colleges are invented. No real resumes were used. Regenerate with:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python ..\scripts\generate_synthetic_data.py
```
The generator is deterministic (fixed random seed), so the files are the same every time.

## Contents
| Path | What |
|---|---|
| `synthetic_jobs/jobs.json` | 10 job descriptions, one per role family (archetype) |
| `synthetic_candidates/cand01..cand30` | 30 resumes: 3 per role family (0, 3 and 7 years of experience), in 3 layouts (2 PDF styles + 1 DOCX style) |
| `synthetic_candidates/manifest.json` | Design facts (archetype, years). Used only for labels — the app never reads it |
| `labels.json` | Relevance label (0–3) for every job × candidate pair (300 labels) |

Within a role family the three candidates use different but realistic stacks — e.g. the Python
backend family has Django, FastAPI and Flask variants, and one mobile candidate is an iOS developer.

## Label rule (written before the matching code was tuned)

Role families that are "adjacent" (share a lot of skills):

| Family | Adjacent to |
|---|---|
| python_backend | java_backend, fullstack_js, data_engineering |
| java_backend | python_backend |
| frontend | fullstack_js, mobile |
| fullstack_js | frontend, python_backend |
| data_science | ml_nlp, data_engineering |
| ml_nlp | data_science |
| data_engineering | data_science, python_backend |
| devops | python_backend |
| mobile | frontend |
| qa_automation | java_backend, python_backend |

(Adjacency is treated as two-way.)

For a job with minimum experience *E* and a candidate with *Y* years:

| Label | Rule |
|---|---|
| 3 | Same family **and** Y ≥ E |
| 2 | Same family but Y < E, **or** adjacent family and Y ≥ E |
| 1 | Adjacent family and Y < E |
| 0 | Any other family |

A candidate is counted as **relevant** when the label is 2 or 3.

These labels depend only on the design manifest. They were not changed after looking at
evaluation results. Results are in `docs/matching_evaluation.md`.
