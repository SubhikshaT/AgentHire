# AI methodology

AgentHire uses six logical agents (plain Python classes in `backend/app/ai/agents/`). Each has typed
inputs and outputs (Pydantic). Everything that decides a **score** is deterministic code; the LLM is
only used to *write* interview questions, follow-ups and answer feedback, and every LLM output is
validated before it is stored.

| Agent | Input | Output | Uses LLM? |
|---|---|---|---|
| Resume Intelligence | resume text | profile + skills with evidence | No (rules + spaCy + taxonomy) |
| Job Analysis | job description | required / preferred skills, experience, education, certs | No (rules + taxonomy) |
| Candidate Matching | job + profile | 6-part score, explanation, evidence | No (embeddings + formulas) |
| Interview Generation | job, skills, gaps, resume chunks | questions with expected concepts + rubric | Optional (question bank otherwise) |
| Interview Evaluation | question, rubric, answer | 5 dimension scores, verdict, feedback | Yes (otherwise answers stay *pending*) |
| Learning Recommendation | skill gaps | resources from a curated list | No |

## 1. Resume parsing
1. **Validation** – extension *and* file signature (`%PDF-` / DOCX zip with `word/document.xml`), max 10 MB, SHA-256 duplicate check.
2. **Extraction** – PyMuPDF (PDF) / python-docx (DOCX, including tables). Image-only PDFs fail with a clear message (no OCR).
3. **Cleaning** – Unicode normalization, whitespace, broken hyphenation.
4. **Sections** – ~70 heading variants mapped to: summary, skills, experience, education, projects, certifications, achievements, other.
5. **Fields** – email/phone by regex; name by spaCy `PERSON` in the header, then a capitalised-line rule; education by degree-level patterns; experience by date ranges (`Jun 2021 – Present`, `05/2019 to 04/2023`, `2018 - 2020`); projects and certifications per line.
6. **Total experience** – sum of full-time periods with overlaps merged; internships excluded. `null` if no dated entries.
7. **Skills** – scanned with the taxonomy (150 skills, synonyms). Ambiguous names (C, R, Go, "rest", "spring"…) only count inside a skills section. Each skill keeps the exact line and section it came from.

Nothing is invented: missing fields stay empty. People can correct any field; corrected fields are marked
`manually_verified` and are never overwritten by re-parsing.

## 2. Skill taxonomy
`backend/app/ai/data/skill_taxonomy.json` – 150 hand-curated skills.
- `synonyms` = the *same* skill (e.g. Postgres = PostgreSQL) → full credit.
- `related` = a *different*, adjacent skill (e.g. Django ↔ FastAPI) → half credit, labelled "related, not equivalent".
Related links are made two-way when loaded.

## 3. Hybrid match score
Each component is in 0–1. Overall = 100 × Σ(weightᵢ × componentᵢ) / Σ weights.

| Component | Default weight | Formula |
|---|---:|---|
| Semantic similarity | 35 | cosine(job-requirements embedding, candidate-profile embedding), mapped linearly from [0.20, 0.80] to [0, 1] and clamped |
| Required skills | 30 | mean over required skills: exact/synonym 1.0, related 0.5, missing 0 |
| Preferred skills | 10 | same over preferred skills; 1.0 if the job lists none |
| Experience | 15 | 1.0 if no minimum; min(years / required, 1); 0.5 if years unknown (flagged) |
| Education | 5 | 1.0 level + field match (field families: CS/IT/SE…), 0.5 level only, 0 otherwise; 1.0 if no requirement |
| Certifications | 5 | share of job-listed certifications found (taxonomy or ≥50% token overlap); 1.0 if none listed |

- Weights are per recruiter (Settings), validated to sum to exactly 100. The weights used are stored with every match.
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (384 dims, CPU). The candidate text contains summary, skills,
  experience, projects and education — **never name, email, phone or address**.
- The cosine value is **not a probability**; the explanation says so.
- A **keyword-only baseline** (share of job skill names literally in the resume text, no synonyms) is stored for comparison.

### Explanation stored with every match
Breakdown (raw value, weight, contribution per component), matched skills with evidence text and section,
related-only skills with a note, missing skills, experience/education/certification notes, strengths, gaps,
unverified skills, and **RAG evidence**: for each missing or related-only skill the closest resume chunk is
retrieved by vector search and shown with its similarity.

## 4. RAG (where retrieval is used)
- Resume sections are split into chunks of ≤ 300 words and embedded (`resume_chunks`).
- **Evidence retrieval** – closest chunk for each gap skill (shown in the match explanation).
- **Question grounding** – the top project/experience chunks for the job are given to the question generator, so questions refer to real resume content.
- Search runs in PostgreSQL with pgvector (`<=>` cosine distance) or in Python/NumPy when `VECTOR_BACKEND=python`. Both paths are tested.

## 5. Interview questions
- Categories: Programming, DSA, DBMS, OS, Networks, Software Engineering, System Design, Project-Based, Behavioral; 3 difficulty levels; 3–15 questions.
- **With an LLM:** prompt `qgen-1.0` gets job requirements, candidate skills, gaps and retrieved project chunks (wrapped as untrusted data). Output must validate against a schema (category, difficulty, ≥1 expected concept, rubric lines, time limit). Duplicates and unknown categories are dropped.
- **Without an LLM (or if the LLM output is invalid after retries):** questions come from `data/question_bank.json` (≥ 10 per category per difficulty, 270+ total), ranked by overlap with the candidate's gaps, the job's skills and the candidate's skills. Project questions are filled with the candidate's real project names.
- Recruiters can edit, reorder, add and delete questions before the interview starts.
- Follow-ups: at most one per question, only with an LLM and only if half or more of the expected concepts are missing.

## 6. Answer evaluation (rubric `rubric-1.0`)
| Dimension | Default weight |
|---|---:|
| Technical correctness | 35 |
| Conceptual understanding | 25 |
| Problem-solving approach | 20 |
| Clarity | 10 |
| Relevance | 10 |

- The LLM (prompt `eval-1.0`) returns 0–10 per dimension, a verdict (`correct | partially_correct | incorrect | insufficient`), strengths, weaknesses, missing concepts, explanation, improvement and quotes.
- **The weighted 0–100 answer score is computed by AgentHire code**, not by the model.
- Evidence quotes that are not exact substrings of the answer are removed (count recorded).
- Answers with fewer than 5 words are marked `insufficient` with zero scores by rule (no LLM needed).
- Without an LLM, answers stay **`pending_llm`**. A "basic concept coverage check" (which expected concepts are mentioned) is shown, clearly labelled as *not a score*. Nothing is invented.
- Interview total = average of answer scores, only when every answer is evaluated.

## 7. LLM safety
- One provider interface: Ollama (local, default `qwen2.5:7b`), Gemini (optional), or none. A fake provider exists **only for tests**.
- System guard: text inside `<untrusted_data>` is data, never instructions. Closing tags inside user text are neutralised.
- JSON only → Pydantic validation → up to 2 retries with the validation error → otherwise a clean failure.
- Max response size, request timeout, rate limits on LLM endpoints.
- AI text is rendered as plain text (React escaping; no raw HTML).
- No personal identifiers in evaluation prompts. Gemini mode shows a notice that data goes to Google.

## 8. AI audit
Every generation/evaluation call is stored in `ai_audit_logs`: agent, provider, model id, prompt version,
rubric version, input record ids, output record, duration, retries, validation result, error, and whether
a person later edited the output. Recruiters can browse it under *Skill Analytics → AI audit*.

## 9. Learning recommendations
Resources come only from `data/learning_resources.json` (official docs and well-known free courses).
Order: missing required skills, then related-only, then preferred. If a skill has no direct resource,
the closest related skill's resource is used and labelled. `scripts/check_learning_links.py` checks the URLs.

## 10. Fairness
- No protected characteristics are stored or inferred; photos are not extracted.
- Name, email, phone are excluded from embeddings and LLM prompts (a test checks that adding them does not change the score).
- The system never moves a candidate to *Rejected*; *Selected* and *Rejected* need explicit confirmation.

## 11. Evaluation
See `matching_evaluation.md` – keyword baseline vs semantic vs hybrid on the labelled synthetic set.
